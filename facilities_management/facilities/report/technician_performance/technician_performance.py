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
		{"label": _("Technician"), "fieldname": "assigned_to", "fieldtype": "Link",
		 "options": "User", "width": 180},
		{"label": _("Completed Orders"), "fieldname": "completed_count", "fieldtype": "Int", "width": 130},
		{"label": _("Open Orders"), "fieldname": "open_count", "fieldtype": "Int", "width": 110},
		{"label": _("Avg Turnaround (hrs)"), "fieldname": "avg_turnaround", "fieldtype": "Float", "width": 150},
		{"label": _("Avg Client Rating"), "fieldname": "avg_rating", "fieldtype": "Float", "width": 130},
	]


def get_data(filters):
	rows = frappe.get_all(
		"Facilities Work Order",
		filters={"assigned_to": ["is", "set"]},
		fields=["assigned_to", "status", "started_on", "completed_on", "rating"],
	)

	by_tech = {}
	for r in rows:
		bucket = by_tech.setdefault(r.assigned_to, {
			"completed_count": 0, "open_count": 0, "turnarounds": [], "ratings": [],
		})
		if r.status in ("Completed", "Closed"):
			bucket["completed_count"] += 1
			if r.started_on and r.completed_on:
				bucket["turnarounds"].append(time_diff_in_hours(r.completed_on, r.started_on))
			if r.rating:
				bucket["ratings"].append(r.rating)
		elif r.status not in ("Cancelled", "Rejected"):
			bucket["open_count"] += 1

	result = []
	for tech, b in by_tech.items():
		result.append({
			"assigned_to": tech,
			"completed_count": b["completed_count"],
			"open_count": b["open_count"],
			"avg_turnaround": round(sum(b["turnarounds"]) / len(b["turnarounds"]), 1) if b["turnarounds"] else None,
			"avg_rating": round(sum(b["ratings"]) / len(b["ratings"]), 2) if b["ratings"] else None,
		})
	result.sort(key=lambda x: x["completed_count"], reverse=True)
	return result
