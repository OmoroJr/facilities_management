# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""NTSA vehicle inspection tracking: status, reminders and automatic planned bookings."""

from types import SimpleNamespace

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, get_url_to_form, getdate, nowdate

VEHICLE = "Facility Vehicle"
BOOKING = "Facilities NTSA Booking"
DEFAULT_REMINDER_DAYS = (30, 14, 7, 3, 1)
DEFAULT_APPOINTMENT_DAYS = (3, 1, 0)


def parse_days(value, default=DEFAULT_REMINDER_DAYS):
	""""30, 14,7" -> [30, 14, 7]. Ignores anything that is not a whole number."""
	days = set()
	for part in str(value or "").split(","):
		part = part.strip()
		if part.isdigit():
			days.add(int(part))
	return sorted(days, reverse=True) or list(default)


def get_soon_days():
	"""A vehicle is Due Soon from the largest reminder interval onwards."""
	settings = frappe.get_cached_doc("Facilities Settings")
	return max(parse_days(settings.get("ntsa_reminder_days")))


def compute_status(required, due, soon_days=None, today=None):
	if not cint(required):
		return "Not Required"
	if not due:
		return "Unknown"
	days_left = date_diff(due, today or nowdate())
	if days_left < 0:
		return "Overdue"
	soon = get_soon_days() if soon_days is None else soon_days
	return "Due Soon" if days_left <= soon else "Valid"


# (label, "required" field, expiry field, status field) for each thing a vehicle must keep valid
COMPLIANCE_ITEMS = (
	("NTSA Inspection", "ntsa_inspection_required", "ntsa_inspection_due", "ntsa_status"),
	("Insurance", "insurance_required", "insurance_expiry", "insurance_status"),
	("Speed Governor", "speed_governor_required", "governor_expiry", "governor_status"),
)
STATUS_FIELDS = [item[3] for item in COMPLIANCE_ITEMS]


def compute_all_statuses(row):
	"""{status field: status} for a vehicle (a document or a row)."""
	soon = get_soon_days()
	return {status_field: compute_status(row.get(req), row.get(due), soon) for _label, req, due, status_field in COMPLIANCE_ITEMS}


def refresh_vehicle_status(vehicle):
	fields = [f for item in COMPLIANCE_ITEMS for f in item[1:]]
	row = frappe.db.get_value(VEHICLE, vehicle, fields, as_dict=True)
	if not row:
		return
	changes = {f: v for f, v in compute_all_statuses(row).items() if v != row.get(f)}
	if changes:
		frappe.db.set_value(VEHICLE, vehicle, changes, update_modified=False)


def driver_user(vehicle):
	driver = frappe.db.get_value(VEHICLE, vehicle, "driver")
	return frappe.db.get_value("Employee", driver, "user_id") if driver else None


def notify(vehicle, subject, message, ref_doc, extra_users=None):
	"""Email Facilities Managers, the vehicle's driver and any extra users."""
	from facilities_management.utils.scheduler import _notify_role

	users = [u for u in [driver_user(vehicle), *(extra_users or [])] if u]
	link = f'<a href="{get_url_to_form(ref_doc.doctype, ref_doc.name)}">{ref_doc.name}</a>'
	_notify_role("Facilities Manager", subject, f"{message}<br><br>{link}", extra_users=users,
				 reference_doctype=ref_doc.doctype, reference_name=ref_doc.name)


# ------------------------------------------------------------------ daily jobs

def daily_ntsa_checks():
	for job in (refresh_all_statuses, send_inspection_reminders, send_compliance_reminders, send_appointment_reminders):
		try:
			job()
		except Exception:
			frappe.log_error(title=f"Facilities: NTSA job {job.__name__} failed")


def refresh_all_statuses():
	fields = ["name"] + [f for item in COMPLIANCE_ITEMS for f in item[1:]]
	for v in frappe.get_all(VEHICLE, fields=fields):
		changes = {f: val for f, val in compute_all_statuses(v).items() if val != v.get(f)}
		if changes:
			frappe.db.set_value(VEHICLE, v.name, changes, update_modified=False)


def reminder_due(days_left, milestones, every):
	"""True on a reminder day: a milestone, the due day, the first overdue day, then every N days overdue."""
	if days_left in milestones or days_left == 0:
		return True
	return days_left < 0 and (days_left == -1 or (-days_left) % every == 0)


def send_compliance_reminders():
	"""Insurance and speed governor: the same reminder days as the NTSA inspection, with no booking step."""
	settings = frappe.get_cached_doc("Facilities Settings")
	if settings.get("ntsa_reminders_enabled") is not None and not cint(settings.get("ntsa_reminders_enabled")):
		return
	milestones = parse_days(settings.get("ntsa_reminder_days"))
	every = cint(settings.get("ntsa_overdue_reminder_every_days")) or 7
	today = getdate(nowdate())
	actions = {
		"Insurance": _("Renew the cover and record it as a Vehicle Compliance Record."),
		"Speed Governor": _("Have the speed governor re-certified and record it as a Vehicle Compliance Record."),
	}
	for label, required, expiry, _status in COMPLIANCE_ITEMS[1:]:
		for v in frappe.get_all(VEHICLE, filters={required: 1, expiry: ["is", "set"]},
								fields=["name", "registration_number", "vehicle_name", expiry]):
			days_left = date_diff(v.get(expiry), today)
			if not reminder_due(days_left, milestones, every):
				continue
			name = f"{v.registration_number} ({v.vehicle_name})" if v.vehicle_name else v.registration_number
			when = frappe.utils.formatdate(v.get(expiry))
			if days_left > 0:
				subject = _("{0} expires in {1} days: {2}").format(_(label), days_left, v.registration_number)
				text = _("The {0} for {1} expires on {2}, in {3} day(s).").format(_(label), name, when, days_left)
			elif days_left == 0:
				subject = _("{0} expires TODAY: {1}").format(_(label), v.registration_number)
				text = _("The {0} for {1} expires today ({2}).").format(_(label), name, when)
			else:
				subject = _("{0} EXPIRED {1} days ago: {2}").format(_(label), -days_left, v.registration_number)
				text = _("The {0} for {1} expired on {2}. Do not use the vehicle until it is valid again.").format(_(label), name, when)
			notify(v.name, subject, f"{text} {actions[label]}", SimpleNamespace(doctype=VEHICLE, name=v.name))


def _open_booking(vehicle):
	return frappe.db.get_value(
		BOOKING, {"vehicle": vehicle, "status": ["in", ["Planned", "Booked"]]},
		["name", "status", "appointment_date"], as_dict=True,
	)


def _create_planned_booking(vehicle, days_left):
	today = getdate(nowdate())
	preferred = max(add_days(today, 3), add_days(today, days_left - 7)) if days_left > 0 else add_days(today, 3)
	doc = frappe.get_doc({
		"doctype": BOOKING, "vehicle": vehicle, "service_type": "Motor Vehicle Inspection", "status": "Planned",
		"preferred_date": preferred, "booked_by": None,
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.add_comment("Info", _("Planned automatically because the NTSA inspection is due soon."))
	return SimpleNamespace(name=doc.name, status="Planned", appointment_date=None)


def send_inspection_reminders():
	settings = frappe.get_cached_doc("Facilities Settings")
	if settings.get("ntsa_reminders_enabled") is not None and not cint(settings.get("ntsa_reminders_enabled")):
		return
	milestones = parse_days(settings.get("ntsa_reminder_days"))
	every = cint(settings.get("ntsa_overdue_reminder_every_days")) or 7
	lead = cint(settings.get("ntsa_auto_booking_lead_days") or 30)
	auto_book = settings.get("ntsa_auto_create_booking")
	auto_book = True if auto_book is None else bool(cint(auto_book))
	today = getdate(nowdate())

	vehicles = frappe.get_all(
		VEHICLE, filters={"ntsa_inspection_required": 1, "ntsa_inspection_due": ["is", "set"]},
		fields=["name", "registration_number", "vehicle_name", "ntsa_inspection_due"],
	)
	for v in vehicles:
		days_left = date_diff(v.ntsa_inspection_due, today)
		booking = _open_booking(v.name)
		if auto_book and days_left <= lead and not booking:
			booking = _create_planned_booking(v.name, days_left)

		if not reminder_due(days_left, milestones, every):
			continue
		appointment = booking.appointment_date if booking and booking.status == "Booked" else None
		if days_left >= 0 and appointment and getdate(appointment) >= today and getdate(appointment) <= getdate(v.ntsa_inspection_due):
			continue  # already booked in time: the appointment reminders cover it

		label = f"{v.registration_number} ({v.vehicle_name})" if v.vehicle_name else v.registration_number
		if days_left > 0:
			subject = _("NTSA inspection due in {0} days: {1}").format(days_left, v.registration_number)
			lead_text = _("The NTSA inspection for {0} is due on {1}, in {2} day(s).").format(label, frappe.utils.formatdate(v.ntsa_inspection_due), days_left)
		elif days_left == 0:
			subject = _("NTSA inspection due TODAY: {0}").format(v.registration_number)
			lead_text = _("The NTSA inspection for {0} expires today ({1}).").format(label, frappe.utils.formatdate(v.ntsa_inspection_due))
		else:
			subject = _("NTSA inspection OVERDUE by {0} days: {1}").format(-days_left, v.registration_number)
			lead_text = _("The NTSA inspection for {0} expired on {1}, {2} day(s) ago. Do not use the vehicle until it is inspected.").format(
				label, frappe.utils.formatdate(v.ntsa_inspection_due), -days_left)
		if booking and booking.status == "Booked":
			lead_text += " " + _("An appointment is booked for {0}.").format(frappe.utils.formatdate(booking.appointment_date))
		elif booking:
			lead_text += " " + _("A planned booking exists ({0}): book the appointment with NTSA and update it.").format(booking.name)
		else:
			lead_text += " " + _("Create an NTSA booking for this vehicle.")
		notify(v.name, subject, lead_text, SimpleNamespace(doctype=VEHICLE, name=v.name))


def send_appointment_reminders():
	settings = frappe.get_cached_doc("Facilities Settings")
	days = parse_days(settings.get("ntsa_booking_reminder_days"), DEFAULT_APPOINTMENT_DAYS)
	today = getdate(nowdate())
	for b in frappe.get_all(
		BOOKING, filters={"status": "Booked", "appointment_date": ["is", "set"]},
		fields=["name", "vehicle", "registration_number", "appointment_date", "appointment_time", "inspection_centre", "booking_reference", "booked_by"],
	):
		diff = date_diff(b.appointment_date, today)
		doc = SimpleNamespace(doctype=BOOKING, name=b.name)
		if diff >= 0 and diff in days:
			when = _("today") if diff == 0 else _("in {0} day(s)").format(diff)
			notify(
				b.vehicle,
				_("NTSA appointment {0}: {1}").format(when, b.registration_number),
				_("{0} has an NTSA appointment {1} on {2}{3}{4}. Booking reference: {5}. Take the vehicle registration documents and the booking confirmation.").format(
					b.registration_number, when, frappe.utils.formatdate(b.appointment_date),
					f" at {b.appointment_time}" if b.appointment_time else "",
					f", {b.inspection_centre}" if b.inspection_centre else "", b.booking_reference or "-"),
				doc, extra_users=[b.booked_by],
			)
		elif diff < 0 and -diff in (1, 3, 7):
			notify(
				b.vehicle,
				_("Record the NTSA result: {0}").format(b.registration_number),
				_("The NTSA appointment for {0} was on {1}. Record whether it passed or failed so the inspection due date is updated.").format(
					b.registration_number, frappe.utils.formatdate(b.appointment_date)),
				doc, extra_users=[b.booked_by],
			)
