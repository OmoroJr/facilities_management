# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Schedule"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Preventive Maintenance Schedule", "width": 150},
		{"label": _("Facility Asset"), "fieldname": "facility_asset", "fieldtype": "Link",
		 "options": "Facility Asset", "width": 140},
		{"label": _("Frequency"), "fieldname": "frequency", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Next Due"), "fieldname": "next_due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days Until Due"), "fieldname": "days_until_due", "fieldtype": "Int", "width": 110},
		{"label": _("Compliance"), "fieldname": "compliance", "fieldtype": "Data", "width": 100},
		{"label": _("Assigned Technician"), "fieldname": "assigned_technician", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("Last Work Order"), "fieldname": "last_generated_work_order", "fieldtype": "Link",
		 "options": "Facilities Work Order", "width": 130},
	]


def get_data(filters):
	conditions = {}
	if filters.get("facility_asset"):
		conditions["facility_asset"] = filters["facility_asset"]
	if filters.get("status"):
		conditions["status"] = filters["status"]

	rows = frappe.get_all(
		"Preventive Maintenance Schedule",
		filters=conditions,
		fields=["name", "facility_asset", "frequency", "status", "next_due_date",
				"assigned_technician", "last_generated_work_order"],
		order_by="next_due_date asc",
	)
	now = getdate(today())
	for r in rows:
		if r.next_due_date:
			r["days_until_due"] = (getdate(r.next_due_date) - now).days
			r["compliance"] = _("Overdue") if r["days_until_due"] < 0 else (
				_("Due Soon") if r["days_until_due"] <= 7 else _("On Track")
			)
		else:
			r["days_until_due"] = None
			r["compliance"] = ""
	return rows
