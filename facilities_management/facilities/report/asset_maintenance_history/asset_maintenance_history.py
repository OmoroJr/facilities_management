# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Facility Asset"), "fieldname": "facility_asset", "fieldtype": "Link",
		 "options": "Facility Asset", "width": 150},
		{"label": _("Work Order"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Facilities Work Order", "width": 130},
		{"label": _("Type"), "fieldname": "work_order_type", "fieldtype": "Data", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Completed On"), "fieldname": "completed_on", "fieldtype": "Datetime", "width": 150},
	]


def get_data(filters):
	conditions = {"facility_asset": ["is", "set"]}
	if filters.get("facility_asset"):
		conditions["facility_asset"] = filters["facility_asset"]

	return frappe.get_all(
		"Facilities Work Order",
		filters=conditions,
		fields=["facility_asset", "name", "work_order_type", "status", "completed_on"],
		order_by="facility_asset asc, completed_on desc",
	)
