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
		{"label": _("Request"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Vendor Approval Request", "width": 130},
		{"label": _("Vendor Name"), "fieldname": "vendor_name", "fieldtype": "Data", "width": 180},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Requested By"), "fieldname": "requested_by", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("Approver"), "fieldname": "approver", "fieldtype": "Link",
		 "options": "User", "width": 150},
		{"label": _("Services Offered"), "fieldname": "services_offered", "fieldtype": "Small Text", "width": 200},
		{"label": _("Contact Email"), "fieldname": "contact_email", "fieldtype": "Data", "width": 160},
		{"label": _("Linked Supplier"), "fieldname": "proposed_vendor", "fieldtype": "Link",
		 "options": "Supplier", "width": 150},
	]


def get_data(filters):
	conditions = {}
	if filters.get("status"):
		conditions["status"] = filters["status"]

	return frappe.get_all(
		"Vendor Approval Request",
		filters=conditions,
		fields=["name", "vendor_name", "status", "requested_by", "approver",
				"services_offered", "contact_email", "proposed_vendor"],
		order_by="modified desc",
	)
