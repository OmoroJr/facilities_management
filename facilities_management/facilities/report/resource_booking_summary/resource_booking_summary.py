# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import time_diff_in_hours


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Resource Type"), "fieldname": "resource_type", "fieldtype": "Data", "width": 100},
		{"label": _("Resource"), "fieldname": "resource", "fieldtype": "Dynamic Link",
		 "options": "resource_type_dt", "width": 150},
		{"label": _("Booked By"), "fieldname": "booked_by", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("From"), "fieldname": "from_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": _("To"), "fieldname": "to_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": _("Duration (hrs)"), "fieldname": "duration_hours", "fieldtype": "Float", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Purpose"), "fieldname": "purpose", "fieldtype": "Data", "width": 180},
	]


def get_data(filters):
	rows = []

	room_conditions = {}
	vehicle_conditions = {}
	if filters.get("status"):
		room_conditions["status"] = filters["status"]
		vehicle_conditions["status"] = filters["status"]
	if filters.get("from_date"):
		room_conditions["from_datetime"] = [">=", filters["from_date"]]
		vehicle_conditions["from_datetime"] = [">=", filters["from_date"]]

	for b in frappe.get_all(
		"Room Booking", filters=room_conditions,
		fields=["room as resource", "booked_by", "from_datetime", "to_datetime", "status", "purpose"],
	):
		b["resource_type"] = _("Room")
		b["resource_type_dt"] = "Facility Room"
		rows.append(b)

	for b in frappe.get_all(
		"Vehicle Booking", filters=vehicle_conditions,
		fields=["vehicle as resource", "booked_by", "from_datetime", "to_datetime", "status", "purpose"],
	):
		b["resource_type"] = _("Vehicle")
		b["resource_type_dt"] = "Facility Vehicle"
		rows.append(b)

	for r in rows:
		if r.get("from_datetime") and r.get("to_datetime"):
			r["duration_hours"] = round(time_diff_in_hours(r["to_datetime"], r["from_datetime"]), 1)
		else:
			r["duration_hours"] = None

	rows.sort(key=lambda r: r.get("from_datetime") or "", reverse=True)
	return rows
