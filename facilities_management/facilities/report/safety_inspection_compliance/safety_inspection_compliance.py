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
		{"label": _("Inspection"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Safety Inspection", "width": 130},
		{"label": _("Type"), "fieldname": "inspection_type", "fieldtype": "Data", "width": 130},
		{"label": _("Facility Asset"), "fieldname": "facility_asset", "fieldtype": "Link",
		 "options": "Facility Asset", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Inspection Date"), "fieldname": "inspection_date", "fieldtype": "Date", "width": 110},
		{"label": _("Certification Expiry"), "fieldname": "certification_expiry", "fieldtype": "Date", "width": 130},
		{"label": _("Days To Expiry"), "fieldname": "days_to_expiry", "fieldtype": "Int", "width": 110},
		{"label": _("Corrective Action Required"), "fieldname": "corrective_action_required",
		 "fieldtype": "Check", "width": 130},
		{"label": _("Linked Work Order"), "fieldname": "linked_work_order", "fieldtype": "Link",
		 "options": "Facilities Work Order", "width": 130},
	]


def get_data(filters):
	conditions = {}
	if filters.get("inspection_type"):
		conditions["inspection_type"] = filters["inspection_type"]
	if filters.get("status"):
		conditions["status"] = filters["status"]

	rows = frappe.get_all(
		"Safety Inspection",
		filters=conditions,
		fields=["name", "inspection_type", "facility_asset", "status", "inspection_date",
				"certification_expiry", "corrective_action_required", "linked_work_order"],
		order_by="certification_expiry asc",
	)
	now = getdate(today())
	for r in rows:
		r["days_to_expiry"] = (getdate(r.certification_expiry) - now).days if r.certification_expiry else None
	return rows
