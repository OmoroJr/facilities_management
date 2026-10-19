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


def build_ics(doc, cancel=False, attendees=None):
	label, title, location = _resource(doc)
	booker = frappe.db.get_value("User", doc.booked_by, "email")
	attendees = attendees or [booker]
	attendee = booker
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
	]
	for email in attendees:
		cn = frappe.utils.get_fullname(doc.booked_by) if email == booker else email
		lines.append(f"ATTENDEE;CN={_esc(cn)};RSVP=FALSE:mailto:{email}")
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


@frappe.whitelist()
def send_invite(doctype, name, recipients=None, message=None):
	"""Send (or re-send) the calendar invite for a Confirmed booking.

	Called from the 'Send Calendar Invite' button on the booking form, which is
	also what you reach by clicking an event in the calendar view. `recipients`
	is a comma/newline separated list of emails; blank means the person who
	booked. Returns the list of addresses the invite went to.
	"""
	if doctype not in ("Room Booking", "Vehicle Booking"):
		frappe.throw(_("Invites can only be sent for room and vehicle bookings"))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.status != "Confirmed":
		frappe.throw(_("Only Confirmed bookings can be sent as a calendar invite. Current status: {0}").format(doc.status))

	booker = frappe.db.get_value("User", doc.booked_by, "email") if doc.booked_by else None
	raw = [r.strip() for r in (recipients or "").replace("\n", ",").replace(";", ",").split(",") if r.strip()]
	emails = list(dict.fromkeys(raw or ([booker] if booker else [])))
	if not emails:
		frappe.throw(_("No recipient: add an email address or set Booked By"))
	if len(emails) > 20:
		frappe.throw(_("Please send to 20 recipients or fewer at a time"))
	for e in emails:
		frappe.utils.validate_email_address(e, throw=True)

	label, title, location = _resource(doc)
	when = f"{get_datetime(doc.from_datetime):%a %d %b %Y, %H:%M} - {get_datetime(doc.to_datetime):%H:%M}"
	details = _("{0}: {1}<br>When: {2}<br>Purpose: {3}").format(label, title, when, doc.purpose or "-")
	intro = _("You are invited. A calendar invite is attached - open it to add this booking to your calendar.")
	body = f"{intro}<br><br>" + (f"{frappe.utils.escape_html(message)}<br><br>" if message else "") + details

	frappe.sendmail(
		recipients=emails,
		subject=_("Invitation: {0} - {1}").format(title, when),
		message=body,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		attachments=[{"fname": "booking.ics", "fcontent": build_ics(doc, attendees=emails)}],
	)
	doc.add_comment("Info", _("Calendar invite sent to {0}").format(", ".join(emails)))
	return emails
