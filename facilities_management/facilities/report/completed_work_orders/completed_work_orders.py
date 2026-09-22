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
		{"label": _("Work Order"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Facilities Work Order", "width": 130},
		{"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 220},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link",
		 "options": "Department", "width": 130},
		{"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("Started"), "fieldname": "started_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Completed"), "fieldname": "completed_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Turnaround (hrs)"), "fieldname": "turnaround_hours", "fieldtype": "Float", "width": 130},
		{"label": _("Client Rating"), "fieldname": "rating", "fieldtype": "Float", "width": 100},
	]


def get_data(filters):
	conditions = {"status": ["in", ["Completed", "Closed"]]}
	if filters.get("department"):
		conditions["department"] = filters["department"]
	if filters.get("assigned_to"):
		conditions["assigned_to"] = filters["assigned_to"]

	rows = frappe.get_all(
		"Facilities Work Order",
		filters=conditions,
		fields=["name", "subject", "department", "assigned_to", "started_on", "completed_on", "rating"],
		order_by="completed_on desc",
	)
	for r in rows:
		if r.started_on and r.completed_on:
			r["turnaround_hours"] = round(time_diff_in_hours(r.completed_on, r.started_on), 1)
		else:
			r["turnaround_hours"] = None
	return rows
