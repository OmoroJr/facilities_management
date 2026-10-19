# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from facilities_management.utils.report_helpers import WO, date_range, end_of_day, months_between, pct, start_of_day, summary_card

GROUPS = ["Vendor", "Month", "Asset Category", "Status", "Requested By"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 365)
	group_by = filters.get("group_by") or "Vendor"
	if group_by not in GROUPS:
		frappe.throw(_("Invalid Group By"))
	cond = {"creation": ["between", [start_of_day(from_date), end_of_day(to_date)]]}
	if filters.get("vendor"):
		cond["vendor"] = filters["vendor"]
	if filters.get("status"):
		cond["status"] = filters["status"]
	else:
		cond["status"] = ["not in", ["Draft", "Cancelled"]]
	pos = frappe.get_all(
		"Facilities Purchase Order", filters=cond,
		fields=["name", "vendor", "status", "creation", "total_amount", "facilities_work_order", "requested_by"],
	)
	wo_asset = {}
	wo_names = [p.facilities_work_order for p in pos if p.facilities_work_order]
	if wo_names:
		wo_asset = {w.name: w.facility_asset for w in frappe.get_all(WO, filters={"name": ["in", wo_names]}, fields=["name", "facility_asset"])}
	categories = {}
	assets = {a for a in wo_asset.values() if a}
	if assets:
		categories = {a.name: a.asset_category for a in frappe.get_all("Facility Asset", filters={"name": ["in", list(assets)]}, fields=["name", "asset_category"])}

	def key(p):
		if group_by == "Vendor":
			return p.vendor or _("No Vendor")
		if group_by == "Month":
			return p.creation.strftime("%Y-%m")
		if group_by == "Status":
			return p.status
		if group_by == "Requested By":
			return p.requested_by or _("Unspecified")
		return categories.get(wo_asset.get(p.facilities_work_order)) or _("Not linked to an asset")

	buckets = {}
	if group_by == "Month":
		buckets = {m: [] for m in months_between(from_date, to_date)}
	for p in pos:
		buckets.setdefault(key(p), []).append(p)
	total = sum(p.total_amount or 0 for p in pos)

	data = []
	for k, items in buckets.items():
		amount = sum(i.total_amount or 0 for i in items)
		data.append({
			"group": k, "po_count": len(items), "total_amount": amount,
			"avg_po_value": round(amount / len(items), 2) if items else 0,
			"share_pct": pct(amount, total), "linked_work_orders": len({i.facilities_work_order for i in items if i.facilities_work_order}),
		})
	if group_by != "Month":
		data.sort(key=lambda d: -d["total_amount"])
	top = max(data, key=lambda d: d["total_amount"], default=None)
	summary = [
		summary_card(_("Total Spend"), total, "Currency"),
		summary_card(_("Purchase Orders"), len(pos)),
		summary_card(_("Average PO Value"), round(total / len(pos), 2) if pos else 0, "Currency"),
		summary_card(_("Top {0}").format(_(group_by)), top["group"] if top and top["total_amount"] else "-", "Data"),
	]
	shown = data[:12] if group_by != "Month" else data
	chart = {
		"data": {"labels": [d["group"] for d in shown], "datasets": [{"name": _("Spend"), "values": [d["total_amount"] for d in shown]}]},
		"type": "line" if group_by == "Month" else "bar", "colors": ["#7E57C2"],
	}
	columns = [{"label": _(group_by), "fieldname": "group", "fieldtype": "Data", "width": 200}] + [
		{"label": _("Purchase Orders"), "fieldname": "po_count", "fieldtype": "Int", "width": 120},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Avg PO Value"), "fieldname": "avg_po_value", "fieldtype": "Currency", "width": 130},
		{"label": _("Share of Spend %"), "fieldname": "share_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Linked Work Orders"), "fieldname": "linked_work_orders", "fieldtype": "Int", "width": 130},
	]
	return columns, data, None, chart, summary
