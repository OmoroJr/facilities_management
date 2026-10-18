# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""Email the person who made a Room/Vehicle Booking, with a calendar invite.

  Requested  (on creation)        -> "request received" mail, no invite
  Confirmed  (new, or re-timed)   -> mail + .ics invite (adds / updates the event)
  Cancelled  (was Confirmed)      -> mail + .ics cancellation (removes the event)

Wired in hooks.py: doc_events -> Room Booking / Vehicle Booking -> on_update.
The invite uses a stable UID per booking and an increasing SEQUENCE, so a
re-timed booking updates the same calendar entry instead of duplicating it.
"""

from datetime import timezone
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import get_datetime, get_url_to_form, now_datetime

from facilities_management.utils.notifications import flag_enabled, get_settings


def _utc(value):
	"""Site-timezone naive datetime -> aware UTC datetime."""
	tz = ZoneInfo(frappe.utils.get_system_timezone())
	return get_datetime(value).replace(tzinfo=tz).astimezone(timezone.utc)


def _esc(text):
	return (
		(text or "")
		.replace("\\", "\\\\")
		.replace(";", "\\;")
		.replace(",", "\\,")
		.replace("\r\n", "\\n")
		.replace("\n", "\\n")
	)


def _fold(line):
	"""RFC 5545: lines longer than 75 octets are folded with CRLF + space."""
	raw = line.encode("utf-8")
	if len(raw) <= 75:
		return line
	parts, current = [], b""
	for ch in line:
		b = ch.encode("utf-8")
		if len(current) + len(b) > (75 if not parts else 74):
			parts.append(current)
			current = b""
		current += b
	parts.append(current)
	return "\r\n ".join(p.decode("utf-8") for p in parts)


def _resource(doc):
	"""(label, title, location) describing the booked room or vehicle."""
	if doc.doctype == "Room Booking":
		room = frappe.db.get_value(
			"Facility Room", doc.room, ["room_name", "building", "floor"], as_dict=True
		) or {}
		title = room.get("room_name") or doc.room
		location = ", ".join(x for x in (title, room.get("building"), room.get("floor")) if x)
		return _("Room"), title, location
	vehicle = frappe.db.get_value(
		"Facility Vehicle", doc.vehicle, ["vehicle_name", "registration_number"], as_dict=True
	) or {}
	title = vehicle.get("vehicle_name") or doc.vehicle
	if vehicle.get("registration_number"):
		title = f"{title} ({vehicle.registration_number})"
	return _("Vehicle"), title, doc.get("destination") or ""


def build_ics(doc, cancel=False):
	label, title, location = _resource(doc)
	attendee = frappe.db.get_value("User", doc.booked_by, "email")
	organizer = (
		frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id") or attendee
	)
	stamp = "%Y%m%dT%H%M%SZ"
	summary = f"{label}: {title}" + (f" - {doc.purpose}" if doc.purpose else "")
	description = _esc(
		"\n".join(
			x
			for x in (
				doc.purpose,
				doc.get("notes"),
				_("Booking: {0}").format(doc.name),
				get_url_to_form(doc.doctype, doc.name),
			)
			if x
		)
	)
	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		"PRODID:-//PingTap Solutions//Facilities Management//EN",
		"CALSCALE:GREGORIAN",
		f"METHOD:{'CANCEL' if cancel else 'REQUEST'}",
		"BEGIN:VEVENT",
		f"UID:{frappe.scrub(doc.doctype)}-{doc.name}@{frappe.local.site}",
		f"DTSTAMP:{now_datetime().astimezone(timezone.utc).strftime(stamp)}",
		f"SEQUENCE:{int(get_datetime(doc.modified).timestamp())}",
		f"DTSTART:{_utc(doc.from_datetime).strftime(stamp)}",
		f"DTEND:{_utc(doc.to_datetime).strftime(stamp)}",
		f"SUMMARY:{_esc(summary)}",
		f"DESCRIPTION:{description}",
		f"LOCATION:{_esc(location)}",
		f"STATUS:{'CANCELLED' if cancel else 'CONFIRMED'}",
		f"ORGANIZER:mailto:{organizer}",
		f"ATTENDEE;CN={_esc(frappe.utils.get_fullname(doc.booked_by))};RSVP=FALSE:mailto:{attendee}",
	]
	if not cancel:
		lines += [
			"BEGIN:VALARM",
			"TRIGGER:-PT30M",
			"ACTION:DISPLAY",
			f"DESCRIPTION:{_esc(summary)}",
			"END:VALARM",
		]
	lines += ["END:VEVENT", "END:VCALENDAR"]
	return ("\r\n".join(_fold(l) for l in lines) + "\r\n").encode("utf-8")


def send_booking_email(doc, method=None):
	"""on_update handler for Room Booking and Vehicle Booking."""
	if not doc.booked_by or not doc.from_datetime or not doc.to_datetime:
		return
	settings = get_settings()
	if not settings.enable_email_notifications or not flag_enabled(settings, "email_send_booking_invites"):
		return
	email = frappe.db.get_value("User", doc.booked_by, "email")
	if not email:
		return

	before = doc.get_doc_before_save()
	created = before is None
	status_changed = created or before.status != doc.status
	resource_field = "room" if doc.doctype == "Room Booking" else "vehicle"
	retimed = (not created) and (
		str(before.from_datetime) != str(doc.from_datetime)
		or str(before.to_datetime) != str(doc.to_datetime)
		or before.get(resource_field) != doc.get(resource_field)
	)

	label, title, location = _resource(doc)
	when = f"{get_datetime(doc.from_datetime):%a %d %b %Y, %H:%M} - {get_datetime(doc.to_datetime):%H:%M}"
	details = _("{0}: {1}<br>When: {2}<br>Purpose: {3}<br>Booking: {4}").format(
		label, title, when, doc.purpose or "-", f'<a href="{get_url_to_form(doc.doctype, doc.name)}">{doc.name}</a>'
	)

	attachments, subject, intro = None, None, None
	if doc.status == "Confirmed" and (status_changed or retimed):
		attachments = [{"fname": "booking.ics", "fcontent": build_ics(doc)}]
		subject = _("{0} booking {1}: {2}").format(label, _("updated") if retimed and not status_changed else _("confirmed"), title)
		intro = _("Your booking is confirmed. A calendar invite is attached - open it to add the booking to your calendar.")
	elif doc.status == "Cancelled" and status_changed and not created:
		if before.status == "Confirmed":
			attachments = [{"fname": "booking-cancelled.ics", "fcontent": build_ics(doc, cancel=True)}]
		subject = _("{0} booking cancelled: {1}").format(label, title)
		intro = _("Your booking has been cancelled.")
	elif doc.status == "Requested" and created:
		subject = _("{0} booking request received: {1}").format(label, title)
		intro = _("We have received your booking request. You will get a calendar invite once it is confirmed.")
	else:
		return

	try:
		frappe.sendmail(
			recipients=[email],
			subject=subject,
			message=f"{intro}<br><br>{details}",
			reference_doctype=doc.doctype,
			reference_name=doc.name,
			attachments=attachments,
		)
	except Exception:
		frappe.log_error(title="Facilities: booking invite email failed")
