# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from facilities_management.utils.report_helpers import (
	DONE_STATUSES, WO, avg, date_range, end_of_day, hours_between, median, pct, start_of_day, summary_card, wo_filters,
)

GROUPS = {
	"Technician": "assigned_to", "Work Order Type": "work_order_type", "Priority": "priority",
	"Department": "department", "Source Channel": "source", "Month": None,
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 180)
	group_by = filters.get("group_by") or "Technician"
	if group_by not in GROUPS:
		frappe.throw(_("Invalid Group By"))
	rows = frappe.get_all(
		WO,
		filters=wo_filters(filters, status=["in", DONE_STATUSES],
						   completed_on=["between", [start_of_day(from_date), end_of_day(to_date)]]),
		fields=["name", "creation", "started_on", "completed_on", "sla_due_date", "assigned_to", "work_order_type",
				"priority", "department", "source"],
	)
	buckets = {}
	for r in rows:
		key = r.completed_on.strftime("%Y-%m") if group_by == "Month" else (r.get(GROUPS[group_by]) or _("Unspecified"))
		buckets.setdefault(key, []).append(r)

	data = []
	for key, items in buckets.items():
		res = [hours_between(i.creation, i.completed_on) for i in items]
		timed = [i for i in items if i.sla_due_date]
		met = sum(1 for i in timed if i.completed_on <= i.sla_due_date)
		data.append({
			"group": key, "completed": len(items),
			"avg_response_hrs": avg([hours_between(i.creation, i.started_on) for i in items]),
			"avg_resolution_hrs": avg(res), "median_resolution_hrs": median(res),
			"max_resolution_hrs": max((x for x in res if x is not None), default=None),
			"sla_met": met, "sla_breached": len(timed) - met, "sla_pct": pct(met, len(timed)),
		})
	data.sort(key=lambda d: d["group"] if group_by == "Month" else -d["completed"])

	all_res = [hours_between(r.creation, r.completed_on) for r in rows]
	timed_all = [r for r in rows if r.sla_due_date]
	met_all = sum(1 for r in timed_all if r.completed_on <= r.sla_due_date)
	summary = [
		summary_card(_("Completed"), len(rows)),
		summary_card(_("Avg Response (hrs)"), avg([hours_between(r.creation, r.started_on) for r in rows]) or 0, "Float"),
		summary_card(_("Avg Resolution (hrs)"), avg(all_res) or 0, "Float"),
		summary_card(_("Median Resolution (hrs)"), median(all_res) or 0, "Float"),
		summary_card(_("SLA Met %"), pct(met_all, len(timed_all)) or 0, "Percent",
					 "Green" if (pct(met_all, len(timed_all)) or 0) >= 90 else "Orange"),
	]
	top = data[:15]
	chart = {
		"data": {"labels": [d["group"] for d in top], "datasets": [
			{"name": _("Avg Response (hrs)"), "values": [d["avg_response_hrs"] or 0 for d in top]},
			{"name": _("Avg Resolution (hrs)"), "values": [d["avg_resolution_hrs"] or 0 for d in top]},
		]},
		"type": "line" if group_by == "Month" else "bar",
	}
	columns = [{"label": _(group_by), "fieldname": "group", "fieldtype": "Data", "width": 190}] + [
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 90},
		{"label": _("Avg Response (hrs)"), "fieldname": "avg_response_hrs", "fieldtype": "Float", "precision": 1, "width": 130},
		{"label": _("Avg Resolution (hrs)"), "fieldname": "avg_resolution_hrs", "fieldtype": "Float", "precision": 1, "width": 140},
		{"label": _("Median Resolution (hrs)"), "fieldname": "median_resolution_hrs", "fieldtype": "Float", "precision": 1, "width": 150},
		{"label": _("Slowest (hrs)"), "fieldname": "max_resolution_hrs", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("SLA Met"), "fieldname": "sla_met", "fieldtype": "Int", "width": 80},
		{"label": _("SLA Breached"), "fieldname": "sla_breached", "fieldtype": "Int", "width": 100},
		{"label": _("SLA Met %"), "fieldname": "sla_pct", "fieldtype": "Percent", "width": 90},
	]
	return columns, data, None, chart, summary
