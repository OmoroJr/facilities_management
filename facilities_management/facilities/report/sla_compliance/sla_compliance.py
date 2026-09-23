# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
CLOSED_STATUSES = ("Completed", "Closed")
EXCLUDED_STATUSES = ("Cancelled", "Rejected", "Draft")


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 100},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 80},
		{"label": _("Met SLA"), "fieldname": "met", "fieldtype": "Int", "width": 90},
		{"label": _("Breached SLA"), "fieldname": "breached", "fieldtype": "Int", "width": 110},
		{"label": _("Still Open (within SLA)"), "fieldname": "open_within_sla", "fieldtype": "Int", "width": 150},
		{"label": _("Still Open (overdue)"), "fieldname": "open_overdue", "fieldtype": "Int", "width": 140},
		{"label": _("Compliance %"), "fieldname": "compliance_pct", "fieldtype": "Percent", "width": 110},
	]


def get_data(filters):
	conditions = {"status": ["not in", EXCLUDED_STATUSES]}
	if filters.get("department"):
		conditions["department"] = filters["department"]
	if filters.get("priority"):
		conditions["priority"] = filters["priority"]

	rows = frappe.get_all(
		"Facilities Work Order",
		filters=conditions,
		fields=["priority", "status", "sla_due_date", "completed_on"],
	)

	now = now_datetime()
	buckets = {p: {"total": 0, "met": 0, "breached": 0, "open_within_sla": 0, "open_overdue": 0} for p in PRIORITY_ORDER}

	for r in rows:
		bucket = buckets.setdefault(r.priority or "Medium", {
			"total": 0, "met": 0, "breached": 0, "open_within_sla": 0, "open_overdue": 0,
		})
		bucket["total"] += 1
		if r.status in CLOSED_STATUSES:
			if r.sla_due_date and r.completed_on and r.completed_on > r.sla_due_date:
				bucket["breached"] += 1
			else:
				bucket["met"] += 1
		else:
			if r.sla_due_date and r.sla_due_date < now:
				bucket["open_overdue"] += 1
			else:
				bucket["open_within_sla"] += 1

	result = []
	for priority in PRIORITY_ORDER:
		b = buckets.get(priority)
		if not b or not b["total"]:
			continue
		closed = b["met"] + b["breached"]
		compliance = round((b["met"] / closed) * 100, 1) if closed else None
		result.append({"priority": priority, "compliance_pct": compliance, **b})
	return result


def get_chart(data):
	if not data:
		return None
	return {
		"data": {
			"labels": [r["priority"] for r in data],
			"datasets": [
				{"name": _("Met"), "values": [r["met"] for r in data]},
				{"name": _("Breached"), "values": [r["breached"] for r in data]},
			],
		},
		"type": "bar",
	}
