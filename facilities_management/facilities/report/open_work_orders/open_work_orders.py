# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

OPEN_STATUSES = [
	"Draft", "Submitted", "Pending Approval", "Approved",
	"Assigned", "In Progress", "On Hold",
]


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
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 90},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link",
		 "options": "Department", "width": 130},
		{"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("SLA Due"), "fieldname": "sla_due_date", "fieldtype": "Datetime", "width": 160},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Data", "width": 80},
	]


def get_data(filters):
	conditions = {"status": ["in", OPEN_STATUSES]}
	if filters.get("department"):
		conditions["department"] = filters["department"]
	if filters.get("priority"):
		conditions["priority"] = filters["priority"]

	rows = frappe.get_all(
		"Facilities Work Order",
		filters=conditions,
		fields=["name", "subject", "status", "priority", "department", "assigned_to", "sla_due_date"],
		order_by="priority desc, sla_due_date asc",
	)
	now = now_datetime()
	for r in rows:
		r["overdue"] = _("Yes") if (r.sla_due_date and r.sla_due_date < now) else _("No")
	return rows
