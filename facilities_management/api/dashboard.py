# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, today

from facilities_management.utils.report_helpers import DONE_STATUSES, OPEN_STATUSES, WO, avg, hours_between, pct


def _check():
	if not frappe.has_permission(WO, "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def overdue_work_orders():
	_check()
	n = frappe.db.count(WO, {"status": ["in", OPEN_STATUSES], "sla_due_date": ["<", now_datetime()]})
	return {"value": n, "fieldtype": "Int", "route": ["query-report", "Work Order Aging"], "route_options": {"overdue_only": 1}}


@frappe.whitelist()
def sla_compliance_30d():
	_check()
	rows = frappe.get_all(
		WO, filters={"status": ["in", DONE_STATUSES], "completed_on": [">=", add_days(today(), -30)], "sla_due_date": ["is", "set"]},
		fields=["completed_on", "sla_due_date"],
	)
	met = sum(1 for r in rows if r.completed_on <= r.sla_due_date)
	return {"value": pct(met, len(rows)) or 0, "fieldtype": "Percent", "route": ["query-report", "Response and Resolution Time"], "route_options": {"group_by": "Priority"}}


@frappe.whitelist()
def avg_resolution_hours_30d():
	_check()
	rows = frappe.get_all(WO, filters={"status": ["in", DONE_STATUSES], "completed_on": [">=", add_days(today(), -30)]}, fields=["creation", "completed_on"])
	return {"value": avg([hours_between(r.creation, r.completed_on) for r in rows]) or 0, "fieldtype": "Float", "route": ["query-report", "Response and Resolution Time"]}


@frappe.whitelist()
def warranties_expiring_90d():
	frappe.has_permission("Facility Asset", "read", throw=True)
	n = frappe.db.count("Facility Asset", {"warranty_expiry": ["between", [today(), add_days(today(), 90)]], "status": ["not in", ["Decommissioned", "Disposed"]]})
	return {"value": n, "fieldtype": "Int", "route": ["query-report", "Asset Lifecycle and Warranty"], "route_options": {"warranty_state": "Expiring (90 days)"}}


@frappe.whitelist()
def contracts_expiring_60d():
	frappe.has_permission("Facilities Maintenance Contract", "read", throw=True)
	n = frappe.db.count("Facilities Maintenance Contract", {"status": ["in", ["Active", "Pending Renewal"]], "end_date": ["between", [today(), add_days(today(), 60)]]})
	return {"value": n, "fieldtype": "Int", "route": ["List", "Facilities Maintenance Contract"], "route_options": {"status": "Pending Renewal"}}


@frappe.whitelist()
def overdue_tickets():
	frappe.has_permission("Facilities Ticket", "read", throw=True)
	n = frappe.db.count(
		"Facilities Ticket",
		{"status": ["in", ["Open", "In Progress"]], "resolution_due": ["<", now_datetime()]},
	)
	return {"value": n, "fieldtype": "Int", "route": ["List", "Facilities Ticket"], "route_options": {"status": ["in", ["Open", "In Progress"]]}}


@frappe.whitelist()
def ntsa_due_soon():
	from facilities_management.utils.ntsa import get_soon_days

	frappe.has_permission("Facility Vehicle", "read", throw=True)
	today = frappe.utils.nowdate()
	n = frappe.db.count("Facility Vehicle", {
		"ntsa_inspection_required": 1,
		"ntsa_inspection_due": ["between", [today, frappe.utils.add_days(today, get_soon_days())]],
	})
	return {"value": n, "fieldtype": "Int", "route": ["List", "Facility Vehicle"], "route_options": {"ntsa_status": "Due Soon"}}


@frappe.whitelist()
def ntsa_overdue():
	frappe.has_permission("Facility Vehicle", "read", throw=True)
	n = frappe.db.count("Facility Vehicle", {"ntsa_inspection_required": 1, "ntsa_inspection_due": ["<", frappe.utils.nowdate()]})
	return {"value": n, "fieldtype": "Int", "route": ["List", "Facility Vehicle"], "route_options": {"ntsa_status": "Overdue"}}


@frappe.whitelist()
def vehicle_compliance_expired():
	"""Vehicles with an expired NTSA inspection, insurance or speed governor."""
	from facilities_management.utils.ntsa import COMPLIANCE_ITEMS

	frappe.has_permission("Facility Vehicle", "read", throw=True)
	today = frappe.utils.nowdate()
	names = set()
	for _label, required, expiry, _status in COMPLIANCE_ITEMS:
		names.update(frappe.get_all("Facility Vehicle", filters={required: 1, expiry: ["<", today]}, pluck="name"))
	return {"value": len(names), "fieldtype": "Int", "route": ["query-report", "Vehicle Compliance Register"]}
