# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from facilities_management.utils.report_helpers import (
	DONE_STATUSES, WO, avg, date_range, end_of_day, pct, start_of_day, stars, summary_card, wo_filters,
)

GROUPS = {"Technician": "assigned_to", "Work Order Type": "work_order_type", "Department": "department",
		  "Source Channel": "source", "Month": None}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 365)
	group_by = filters.get("group_by") or "Technician"
	if group_by not in GROUPS:
		frappe.throw(_("Invalid Group By"))
	rows = frappe.get_all(
		WO,
		filters=wo_filters(filters, status=["in", DONE_STATUSES],
						   completed_on=["between", [start_of_day(from_date), end_of_day(to_date)]]),
		fields=["name", "completed_on", "rating", "assigned_to", "work_order_type", "department", "source"],
	)
	buckets = {}
	for r in rows:
		key = r.completed_on.strftime("%Y-%m") if group_by == "Month" else (r.get(GROUPS[group_by]) or _("Unspecified"))
		buckets.setdefault(key, []).append(r)

	data = []
	for key, items in buckets.items():
		rated = [stars(i.rating) for i in items if i.rating]
		dist = {n: sum(1 for x in rated if round(x) == n) for n in range(1, 6)}
		happy = sum(1 for x in rated if x >= 4)
		data.append({
			"group": key, "completed": len(items), "rated": len(rated),
			"response_rate": pct(len(rated), len(items)), "avg_rating": avg(rated),
			"csat_pct": pct(happy, len(rated)),
			"five": dist[5], "four": dist[4], "three": dist[3], "two": dist[2], "one": dist[1],
		})
	data.sort(key=lambda d: d["group"] if group_by == "Month" else -(d["avg_rating"] or 0))
	if filters.get("min_ratings"):
		data = [d for d in data if d["rated"] >= int(filters["min_ratings"])]

	all_rated = [stars(r.rating) for r in rows if r.rating]
	happy_all = sum(1 for x in all_rated if x >= 4)
	summary = [
		summary_card(_("Completed Tickets"), len(rows)),
		summary_card(_("Rated"), len(all_rated)),
		summary_card(_("Response Rate %"), pct(len(all_rated), len(rows)) or 0, "Percent"),
		summary_card(_("Avg Rating (of 5)"), avg(all_rated) or 0, "Float",
					 "Green" if (avg(all_rated) or 0) >= 4 else "Orange" if (avg(all_rated) or 0) >= 3 else "Red"),
		summary_card(_("CSAT % (4-5 stars)"), pct(happy_all, len(all_rated)) or 0, "Percent"),
	]
	top = data[:15]
	chart = {
		"data": {"labels": [d["group"] for d in top], "datasets": [{"name": _("Avg Rating"), "values": [d["avg_rating"] or 0 for d in top]}]},
		"type": "line" if group_by == "Month" else "bar", "colors": ["#F5A623"],
	}
	columns = [{"label": _(group_by), "fieldname": "group", "fieldtype": "Data", "width": 190}] + [
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 90},
		{"label": _("Rated"), "fieldname": "rated", "fieldtype": "Int", "width": 70},
		{"label": _("Response Rate %"), "fieldname": "response_rate", "fieldtype": "Percent", "width": 120},
		{"label": _("Avg Rating (of 5)"), "fieldname": "avg_rating", "fieldtype": "Float", "precision": 1, "width": 120},
		{"label": _("CSAT %"), "fieldname": "csat_pct", "fieldtype": "Percent", "width": 90},
		{"label": _("5 star"), "fieldname": "five", "fieldtype": "Int", "width": 70},
		{"label": _("4 star"), "fieldname": "four", "fieldtype": "Int", "width": 70},
		{"label": _("3 star"), "fieldname": "three", "fieldtype": "Int", "width": 70},
		{"label": _("2 star"), "fieldname": "two", "fieldtype": "Int", "width": 70},
		{"label": _("1 star"), "fieldname": "one", "fieldtype": "Int", "width": 70},
	]
	return columns, data, None, chart, summary
