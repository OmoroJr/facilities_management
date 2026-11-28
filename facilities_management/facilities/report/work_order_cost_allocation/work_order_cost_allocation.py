# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from facilities_management.utils.report_helpers import WO, date_range, end_of_day, start_of_day

GROUPS = {
	"Cost Category": "cost_category",
	"Department": "department",
	"Charge Account / Cost Center": "cost_center",
	"Approval Method": "approval_method",
	"Status": "status",
}


def execute(filters=None):
	"""Who is paying for the work: estimated cost per cost category, department or charge account."""
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 365)
	group_by = filters.get("group_by") or "Cost Category"
	if group_by not in GROUPS:
		frappe.throw(_("Invalid Group By"))
	field = GROUPS[group_by]

	cond = {
		"creation": ["between", [start_of_day(from_date), end_of_day(to_date)]],
		"status": ["not in", ["Draft", "Cancelled", "Rejected"]],
	}
	for f in ("cost_category", "department"):
		if filters.get(f):
			cond[f] = filters[f]
	rows = frappe.get_all(WO, filters=cond, fields=[field, "estimated_total", "status"])

	buckets = {}
	for row in rows:
		key = row.get(field) or _("Not classified")
		b = buckets.setdefault(key, {"group": key, "count": 0, "estimated_total": 0.0, "open_count": 0})
		b["count"] += 1
		b["estimated_total"] += row.estimated_total or 0
		if row.status not in ("Completed", "Closed"):
			b["open_count"] += 1

	grand = sum(b["estimated_total"] for b in buckets.values())
	data = []
	for b in sorted(buckets.values(), key=lambda x: -x["estimated_total"]):
		b["share"] = round(b["estimated_total"] * 100 / grand, 1) if grand else 0
		data.append(b)

	columns = [
		{"fieldname": "group", "label": _(group_by), "fieldtype": "Data", "width": 260},
		{"fieldname": "count", "label": _("Work Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "open_count", "label": _("Still Open"), "fieldtype": "Int", "width": 100},
		{"fieldname": "estimated_total", "label": _("Estimated Cost"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "share", "label": _("Share of Cost %"), "fieldtype": "Percent", "width": 130},
	]
	chart = {"data": {"labels": [d["group"] for d in data], "datasets": [{"values": [d["estimated_total"] for d in data]}]}, "type": "bar"}
	unclassified = sum(b["count"] for k, b in buckets.items() if k == _("Not classified"))
	message = _("{0} work order(s) are not classified yet.").format(unclassified) if unclassified and group_by == "Cost Category" else None
	return columns, data, message, chart
