# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, nowdate

from facilities_management.utils.ntsa import compute_status


def execute(filters=None):
	filters = frappe._dict(filters or {})
	cond = {}
	if not filters.get("include_not_required"):
		cond["ntsa_inspection_required"] = 1
	if filters.get("vehicle_type"):
		cond["vehicle_type"] = filters.vehicle_type

	vehicles = frappe.get_all(
		"Facility Vehicle", filters=cond,
		fields=["name", "registration_number", "vehicle_name", "vehicle_type", "driver", "last_ntsa_inspection",
				"ntsa_inspection_due", "ntsa_inspection_required", "ntsa_certificate_number"],
	)
	open_bookings = {}
	for b in frappe.get_all("Facilities NTSA Booking", filters={"status": ["in", ["Planned", "Booked"]]},
							fields=["name", "vehicle", "status", "appointment_date"], order_by="creation asc"):
		open_bookings[b.vehicle] = b

	data = []
	for v in vehicles:
		status = compute_status(v.ntsa_inspection_required, v.ntsa_inspection_due)
		if filters.get("ntsa_status") and status != filters.ntsa_status:
			continue
		b = open_bookings.get(v.name)
		data.append({
			"vehicle": v.name, "registration_number": v.registration_number, "vehicle_name": v.vehicle_name,
			"vehicle_type": v.vehicle_type, "driver": v.driver, "last_ntsa_inspection": v.last_ntsa_inspection,
			"ntsa_inspection_due": v.ntsa_inspection_due, "certificate": v.ntsa_certificate_number,
			"days_left": date_diff(v.ntsa_inspection_due, nowdate()) if v.ntsa_inspection_due else None,
			"ntsa_status": status, "booking": b.name if b else None, "booking_status": b.status if b else None,
			"appointment_date": b.appointment_date if b else None,
		})
	data.sort(key=lambda r: (r["days_left"] is None, r["days_left"] if r["days_left"] is not None else 0))

	columns = [
		{"fieldname": "registration_number", "label": _("Registration"), "fieldtype": "Link", "options": "Facility Vehicle", "width": 120},
		{"fieldname": "vehicle_name", "label": _("Vehicle"), "fieldtype": "Data", "width": 150},
		{"fieldname": "vehicle_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Employee", "width": 130},
		{"fieldname": "last_ntsa_inspection", "label": _("Last Inspection"), "fieldtype": "Date", "width": 115},
		{"fieldname": "ntsa_inspection_due", "label": _("Due / Expiry"), "fieldtype": "Date", "width": 115},
		{"fieldname": "days_left", "label": _("Days Left"), "fieldtype": "Int", "width": 90},
		{"fieldname": "ntsa_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "booking", "label": _("Open Booking"), "fieldtype": "Link", "options": "Facilities NTSA Booking", "width": 140},
		{"fieldname": "booking_status", "label": _("Booking Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "appointment_date", "label": _("Appointment"), "fieldtype": "Date", "width": 110},
	]
	counts = {}
	for row in data:
		counts[row["ntsa_status"]] = counts.get(row["ntsa_status"], 0) + 1
	chart = {"data": {"labels": list(counts), "datasets": [{"values": list(counts.values())}]}, "type": "donut"}
	return columns, data, None, chart
