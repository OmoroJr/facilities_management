# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

from facilities_management.utils.report_helpers import OPEN_STATUSES, WO, summary_card, wo_filters

BUCKETS = [("0-2 days", 0, 2), ("3-7 days", 3, 7), ("8-14 days", 8, 14), ("15-30 days", 15, 30), ("30+ days", 31, 10**6)]


def bucket_for(age_days):
	for label, lo, hi in BUCKETS:
		if lo <= age_days <= hi:
			return label
	return BUCKETS[-1][0]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	cond = wo_filters(filters, status=["in", OPEN_STATUSES])
	if filters.get("status"):
		cond["status"] = filters["status"]
	rows = frappe.get_all(
		WO, filters=cond,
		fields=["name", "subject", "status", "priority", "work_order_type", "department", "assigned_to",
				"creation", "sla_due_date", "facility_asset"],
		order_by="creation asc",
	)
	now = now_datetime()
	data, counts, overdue = [], {b[0]: 0 for b in BUCKETS}, 0
	for r in rows:
		age = (now - r.creation).days
		late_hrs = round((now - r.sla_due_date).total_seconds() / 3600, 1) if r.sla_due_date and r.sla_due_date < now else 0
		bucket = bucket_for(age)
		counts[bucket] += 1
		overdue += 1 if late_hrs else 0
		data.append({**r, "age_days": age, "age_bucket": bucket, "overdue_hrs": late_hrs,
					 "sla_state": _("Overdue") if late_hrs else (_("Within SLA") if r.sla_due_date else _("No SLA"))})
	if filters.get("overdue_only"):
		data = [d for d in data if d["overdue_hrs"]]
	data.sort(key=lambda d: (-d["overdue_hrs"], -d["age_days"]))

	oldest = max((d["age_days"] for d in data), default=0)
	summary = [
		summary_card(_("Open Work Orders"), len(rows)),
		summary_card(_("Overdue vs SLA"), overdue, indicator="Red" if overdue else "Green"),
		summary_card(_("Older than 30 days"), counts["30+ days"], indicator="Red" if counts["30+ days"] else "Green"),
		summary_card(_("Oldest (days)"), oldest, indicator="Orange" if oldest > 14 else "Green"),
	]
	chart = {
		"data": {"labels": list(counts), "datasets": [{"name": _("Open Work Orders"), "values": list(counts.values())}]},
		"type": "bar", "colors": ["#E24C4C"],
	}
	return get_columns(), data, None, chart, summary


def get_columns():
	return [
		{"label": _("Work Order"), "fieldname": "name", "fieldtype": "Link", "options": WO, "width": 130},
		{"label": _("Subject"), "fieldname": "subject", "fieldtype": "Data", "width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 80},
		{"label": _("Type"), "fieldname": "work_order_type", "fieldtype": "Data", "width": 130},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
		{"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 150},
		{"label": _("Asset"), "fieldname": "facility_asset", "fieldtype": "Link", "options": "Facility Asset", "width": 130},
		{"label": _("Raised"), "fieldname": "creation", "fieldtype": "Datetime", "width": 150},
		{"label": _("Age (days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Age Bucket"), "fieldname": "age_bucket", "fieldtype": "Data", "width": 100},
		{"label": _("SLA Due"), "fieldname": "sla_due_date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Hours Overdue"), "fieldname": "overdue_hrs", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("SLA State"), "fieldname": "sla_state", "fieldtype": "Data", "width": 100},
	]
