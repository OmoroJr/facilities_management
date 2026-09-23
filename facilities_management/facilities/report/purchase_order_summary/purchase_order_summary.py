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
		{"label": _("Purchase Order"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Facilities Purchase Order", "width": 130},
		{"label": _("Vendor"), "fieldname": "vendor", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Required By"), "fieldname": "required_by", "fieldtype": "Date", "width": 100},
		{"label": _("Linked Work Order"), "fieldname": "facilities_work_order", "fieldtype": "Link",
		 "options": "Facilities Work Order", "width": 130},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = {}
	if filters.get("vendor"):
		conditions["vendor"] = filters["vendor"]
	if filters.get("status"):
		conditions["status"] = filters["status"]

	return frappe.get_all(
		"Facilities Purchase Order",
		filters=conditions,
		fields=["name", "vendor", "status", "required_by", "facilities_work_order", "total_amount"],
		order_by="required_by asc",
	)
