# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

from facilities_management.utils.report_helpers import (
	DONE_STATUSES, OPEN_STATUSES, SLA_STATUSES, WO, avg, date_range, end_of_day, hours_between,
	months_between, pct, start_of_day, stars, summary_card, wo_filters,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 180)
	base = wo_filters(filters)
	fields = ["name", "status", "creation", "started_on", "completed_on", "sla_due_date", "rating"]

	created = frappe.get_all(
		WO, filters={**base, "creation": ["between", [start_of_day(from_date), end_of_day(to_date)]]}, fields=fields,
	)
	completed = frappe.get_all(
		WO,
		filters={**base, "status": ["in", DONE_STATUSES],
				 "completed_on": ["between", [start_of_day(from_date), end_of_day(to_date)]]},
		fields=fields,
	)
	open_now = frappe.get_all(WO, filters={**base, "status": ["in", OPEN_STATUSES]}, fields=["name", "sla_due_date"])
	now = now_datetime()
	overdue = sum(1 for r in open_now if r.sla_due_date and r.sla_due_date < now)

	months = months_between(from_date, to_date)
	by_month = {m: {"created": 0, "completed": 0, "met": 0, "sla_total": 0, "resp": [], "res": [], "rate": []} for m in months}
	for r in created:
		m = r.creation.strftime("%Y-%m")
		if m in by_month:
			by_month[m]["created"] += 1
			by_month[m]["resp"].append(hours_between(r.creation, r.started_on))
	for r in completed:
		m = r.completed_on.strftime("%Y-%m")
		if m not in by_month:
			continue
		b = by_month[m]
		b["completed"] += 1
		b["res"].append(hours_between(r.creation, r.completed_on))
		if r.rating:
			b["rate"].append(stars(r.rating))
		if r.sla_due_date:
			b["sla_total"] += 1
			b["met"] += 1 if r.completed_on <= r.sla_due_date else 0

	data = []
	for m in months:
		b = by_month[m]
		data.append({
			"month": m, "created": b["created"], "completed": b["completed"],
			"net_backlog_change": b["created"] - b["completed"],
			"sla_pct": pct(b["met"], b["sla_total"]),
			"avg_response_hrs": avg(b["resp"]), "avg_resolution_hrs": avg(b["res"]),
			"avg_rating": avg(b["rate"]),
		})

	met = sum(b["met"] for b in by_month.values())
	sla_total = sum(b["sla_total"] for b in by_month.values())
	sla = pct(met, sla_total)
	ratings = [stars(r.rating) for r in completed if r.rating]
	summary = [
		summary_card(_("Work Orders Created"), len(created)),
		summary_card(_("Completed"), len(completed), indicator="Green"),
		summary_card(_("Open Backlog (now)"), len(open_now), indicator="Orange" if open_now else "Green"),
		summary_card(_("Overdue (now)"), overdue, indicator="Red" if overdue else "Green"),
		summary_card(_("SLA Compliance %"), sla if sla is not None else 0, "Percent",
					 "Green" if (sla or 0) >= 90 else "Orange" if (sla or 0) >= 75 else "Red"),
		summary_card(_("Avg Resolution (hrs)"), avg([hours_between(r.creation, r.completed_on) for r in completed]) or 0, "Float"),
		summary_card(_("Avg Rating (of 5)"), avg(ratings) or 0, "Float"),
	]
	chart = {
		"data": {"labels": months, "datasets": [
			{"name": _("Created"), "values": [r["created"] for r in data]},
			{"name": _("Completed"), "values": [r["completed"] for r in data]},
		]},
		"type": "line", "colors": ["#2490EF", "#29A745"],
	}
	return get_columns(), data, None, chart, summary


def get_columns():
	return [
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 90},
		{"label": _("Created"), "fieldname": "created", "fieldtype": "Int", "width": 90},
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 100},
		{"label": _("Net Backlog Change"), "fieldname": "net_backlog_change", "fieldtype": "Int", "width": 130},
		{"label": _("SLA Met %"), "fieldname": "sla_pct", "fieldtype": "Percent", "width": 100},
		{"label": _("Avg Response (hrs)"), "fieldname": "avg_response_hrs", "fieldtype": "Float", "precision": 1, "width": 130},
		{"label": _("Avg Resolution (hrs)"), "fieldname": "avg_resolution_hrs", "fieldtype": "Float", "precision": 1, "width": 140},
		{"label": _("Avg Rating (of 5)"), "fieldname": "avg_rating", "fieldtype": "Float", "precision": 1, "width": 120},
	]
