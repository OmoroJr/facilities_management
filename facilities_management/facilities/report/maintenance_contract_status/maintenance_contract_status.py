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
		{"label": _("Contract"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Facilities Maintenance Contract", "width": 130},
		{"label": _("Title"), "fieldname": "contract_title", "fieldtype": "Data", "width": 180},
		{"label": _("Vendor"), "fieldname": "vendor", "fieldtype": "Link", "options": "Supplier", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days To Expiry"), "fieldname": "days_to_expiry", "fieldtype": "Int", "width": 110},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = {}
	if filters.get("vendor"):
		conditions["vendor"] = filters["vendor"]
	if filters.get("status"):
		conditions["status"] = filters["status"]

	rows = frappe.get_all(
		"Facilities Maintenance Contract",
		filters=conditions,
		fields=["name", "contract_title", "vendor", "status", "start_date", "end_date", "contract_value"],
		order_by="end_date asc",
	)
	now = getdate(today())
	for r in rows:
		r["days_to_expiry"] = (getdate(r.end_date) - now).days if r.end_date else None
	return rows
