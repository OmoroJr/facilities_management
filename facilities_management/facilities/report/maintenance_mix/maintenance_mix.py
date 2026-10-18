# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from facilities_management.utils.report_helpers import WO, date_range, end_of_day, months_between, pct, start_of_day, summary_card

TYPES = ["Preventive Maintenance", "Corrective", "Inspection", "Request"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 365)
	cond = {"creation": ["between", [start_of_day(from_date), end_of_day(to_date)]], "status": ["not in", ["Cancelled", "Rejected", "Draft"]]}
	for key in ("department", "facility_asset"):
		if filters.get(key):
			cond[key] = filters[key]
	rows = frappe.get_all(WO, filters=cond, fields=["creation", "work_order_type"])
	months = months_between(from_date, to_date)
	grid = {m: {t: 0 for t in TYPES} for m in months}
	for r in rows:
		m = r.creation.strftime("%Y-%m")
		if m in grid and r.work_order_type in TYPES:
			grid[m][r.work_order_type] += 1

	data = []
	for m in months:
		g = grid[m]
		planned = g["Preventive Maintenance"] + g["Inspection"]
		maint = planned + g["Corrective"]
		data.append({
			"month": m, "preventive": g["Preventive Maintenance"], "corrective": g["Corrective"],
			"inspection": g["Inspection"], "request": g["Request"], "total": sum(g.values()),
			"planned_pct": pct(planned, maint), "reactive_pct": pct(g["Corrective"], maint),
		})
	prev = sum(g["Preventive Maintenance"] + g["Inspection"] for g in grid.values())
	corr = sum(g["Corrective"] for g in grid.values())
	planned_pct = pct(prev, prev + corr)
	summary = [
		summary_card(_("Preventive + Inspection"), prev, indicator="Green"),
		summary_card(_("Corrective (reactive)"), corr, indicator="Orange"),
		summary_card(_("Planned Work %"), planned_pct or 0, "Percent", "Green" if (planned_pct or 0) >= 60 else "Orange"),
		summary_card(_("Service Requests"), sum(g["Request"] for g in grid.values())),
	]
	chart = {
		"data": {"labels": months, "datasets": [
			{"name": _("Preventive"), "values": [d["preventive"] for d in data]},
			{"name": _("Corrective"), "values": [d["corrective"] for d in data]},
			{"name": _("Inspection"), "values": [d["inspection"] for d in data]},
		]},
		"type": "bar", "barOptions": {"stacked": 1}, "colors": ["#29A745", "#E24C4C", "#2490EF"],
	}
	columns = [
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 90},
		{"label": _("Preventive"), "fieldname": "preventive", "fieldtype": "Int", "width": 100},
		{"label": _("Corrective"), "fieldname": "corrective", "fieldtype": "Int", "width": 100},
		{"label": _("Inspection"), "fieldname": "inspection", "fieldtype": "Int", "width": 100},
		{"label": _("Service Requests"), "fieldname": "request", "fieldtype": "Int", "width": 120},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 80},
		{"label": _("Planned Work %"), "fieldname": "planned_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Reactive Work %"), "fieldname": "reactive_pct", "fieldtype": "Percent", "width": 120},
	]
	return columns, data, None, chart, summary
