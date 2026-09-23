# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"label": _("Asset Code"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Facility Asset", "width": 110},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
		{"label": _("Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 110},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link",
		 "options": "Department", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Criticality"), "fieldname": "criticality", "fieldtype": "Data", "width": 90},
		{"label": _("Warranty Expiry"), "fieldname": "warranty_expiry", "fieldtype": "Date", "width": 110},
		{"label": _("Warranty"), "fieldname": "warranty_status", "fieldtype": "Data", "width": 90},
		{"label": _("Vendor"), "fieldname": "vendor", "fieldtype": "Link", "options": "Supplier", "width": 140},
	]


def get_data(filters):
	conditions = {}
	for f in ("asset_category", "department", "status"):
		if filters.get(f):
			conditions[f] = filters[f]

	rows = frappe.get_all(
		"Facility Asset",
		filters=conditions,
		fields=["name", "asset_name", "asset_category", "department", "status",
				"criticality", "warranty_expiry", "vendor"],
		order_by="asset_category asc, asset_name asc",
	)
	now = getdate(today())
	for r in rows:
		if r.warranty_expiry:
			r["warranty_status"] = _("Expired") if getdate(r.warranty_expiry) < now else _("Active")
		else:
			r["warranty_status"] = ""
	return rows


def get_chart(data):
	counts = {}
	for r in data:
		counts[r["status"]] = counts.get(r["status"], 0) + 1
	if not counts:
		return None
	return {
		"data": {"labels": list(counts.keys()), "datasets": [{"name": _("Assets"), "values": list(counts.values())}]},
		"type": "donut",
	}
