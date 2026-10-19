# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, date_diff

from facilities_management.utils.report_helpers import date_range, end_of_day, pct, start_of_day, summary_card

SOURCES = {
	"Room": ("Room Booking", "room", "Facility Room", "room_name"),
	"Vehicle": ("Vehicle Booking", "vehicle", "Facility Vehicle", "vehicle_name"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 30)
	day_hours = float(filters.get("hours_per_day") or 8)
	if not 0 < day_hours <= 24:
		frappe.throw(_("Hours per Day must be between 1 and 24"))
	span_days = date_diff(to_date, from_date) + 1
	if filters.get("include_weekends"):
		working_days = span_days
	else:  # Mon-Sat; Sundays are not bookable days
		working_days = sum(1 for i in range(span_days) if add_days(from_date, i).weekday() < 6)
	available = working_days * day_hours
	win_start, win_end = start_of_day(from_date), end_of_day(to_date)

	kinds = [filters["resource_type"]] if filters.get("resource_type") else list(SOURCES)
	data, tot_booked, tot_bookings, cancelled = [], 0.0, 0, 0
	for kind in kinds:
		doctype, link, resource_dt, label_field = SOURCES[kind]
		res_filters = {"name": filters["resource"]} if filters.get("resource") and filters.get("resource_type") == kind else {}
		resources = frappe.get_all(resource_dt, filters=res_filters, fields=["name", label_field + " as title"])
		bookings = frappe.get_all(
			doctype,
			filters={"from_datetime": ["<", win_end], "to_datetime": [">", win_start]},
			fields=[link + " as resource", "from_datetime", "to_datetime", "status"],
		)
		per = {r.name: {"hrs": 0.0, "n": 0, "cancelled": 0} for r in resources}
		for b in bookings:
			if b.resource not in per:
				continue
			if b.status == "Cancelled":
				per[b.resource]["cancelled"] += 1
				continue
			if b.status == "Requested" and not filters.get("include_requested"):
				continue
			start, end = max(b.from_datetime, win_start), min(b.to_datetime, win_end)
			per[b.resource]["hrs"] += max((end - start).total_seconds() / 3600, 0)
			per[b.resource]["n"] += 1
		for r in resources:
			p = per[r.name]
			booked = round(p["hrs"], 1)
			tot_booked += booked
			tot_bookings += p["n"]
			cancelled += p["cancelled"]
			util = pct(booked, available)
			data.append({
				"resource_type": kind, "resource": r.name, "title": r.title, "bookings": p["n"], "booked_hours": booked,
				"available_hours": available, "utilization_pct": util, "cancelled": p["cancelled"],
				"band": _("Idle") if (util or 0) < 10 else _("Under-used") if (util or 0) < 40 else _("Healthy") if (util or 0) <= 85 else _("Over-subscribed"),
			})
	data.sort(key=lambda d: -(d["utilization_pct"] or 0))
	overall = pct(tot_booked, available * len(data)) if data else 0
	summary = [
		summary_card(_("Resources"), len(data)),
		summary_card(_("Bookings in Period"), tot_bookings),
		summary_card(_("Booked Hours"), round(tot_booked, 1), "Float"),
		summary_card(_("Overall Utilization %"), overall or 0, "Percent", "Green" if 40 <= (overall or 0) <= 85 else "Orange"),
		summary_card(_("Over-subscribed"), sum(1 for d in data if d["band"] == _("Over-subscribed")), indicator="Red"),
		summary_card(_("Idle (<10%)"), sum(1 for d in data if d["band"] == _("Idle")), indicator="Orange"),
		summary_card(_("Cancelled Bookings"), cancelled),
	]
	top = data[:15]
	chart = {
		"data": {"labels": [d["title"] or d["resource"] for d in top],
				 "datasets": [{"name": _("Utilization %"), "values": [d["utilization_pct"] or 0 for d in top]}]},
		"type": "bar", "colors": ["#2490EF"],
	}
	columns = [
		{"label": _("Type"), "fieldname": "resource_type", "fieldtype": "Data", "width": 80},
		{"label": _("Resource"), "fieldname": "resource", "fieldtype": "Data", "width": 120},
		{"label": _("Name"), "fieldname": "title", "fieldtype": "Data", "width": 190},
		{"label": _("Bookings"), "fieldname": "bookings", "fieldtype": "Int", "width": 90},
		{"label": _("Booked Hours"), "fieldname": "booked_hours", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("Available Hours"), "fieldname": "available_hours", "fieldtype": "Float", "precision": 1, "width": 120},
		{"label": _("Utilization %"), "fieldname": "utilization_pct", "fieldtype": "Percent", "width": 110},
		{"label": _("Band"), "fieldname": "band", "fieldtype": "Data", "width": 120},
		{"label": _("Cancelled"), "fieldname": "cancelled", "fieldtype": "Int", "width": 90},
	]
	return columns, data, None, chart, summary
