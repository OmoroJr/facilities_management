# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, today

from facilities_management.utils.report_helpers import WO, date_range, end_of_day, pct, start_of_day, summary_card


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date, to_date = date_range(filters, 365)
	soon = add_days(today(), int(filters.get("expiry_window") or 60))

	contracts = frappe.get_all(
		"Facilities Maintenance Contract",
		fields=["name", "vendor", "status", "end_date", "contract_value"],
		filters={"vendor": filters["vendor"]} if filters.get("vendor") else {},
	)
	po_filters = {"creation": ["between", [start_of_day(from_date), end_of_day(to_date)]], "status": ["not in", ["Draft", "Cancelled"]]}
	if filters.get("vendor"):
		po_filters["vendor"] = filters["vendor"]
	pos = frappe.get_all("Facilities Purchase Order", filters=po_filters, fields=["name", "vendor", "status", "total_amount", "facilities_work_order"])
	covered = {}
	names = [c.name for c in contracts]
	if names:
		for r in frappe.get_all("Contract Covered Asset", filters={"parent": ["in", names]}, fields=["parent", "count(name) as n"], group_by="parent"):
			covered[r.parent] = r.n

	vendors = {}
	def slot(v):
		return vendors.setdefault(v or _("No Vendor"), {
			"active": 0, "value": 0, "expiring": 0, "expired": 0, "assets": 0, "pos": 0, "received": 0, "spend": 0, "wos": set(),
		})
	for c in contracts:
		s = slot(c.vendor)
		s["assets"] += covered.get(c.name, 0)
		if c.status in ("Active", "Pending Renewal"):
			s["active"] += 1
			s["value"] += c.contract_value or 0
			if c.end_date and str(c.end_date) <= str(soon):
				s["expiring"] += 1
		elif c.status == "Expired":
			s["expired"] += 1
	for p in pos:
		s = slot(p.vendor)
		s["pos"] += 1
		s["spend"] += p.total_amount or 0
		s["received"] += 1 if p.status == "Received" else 0
		if p.facilities_work_order:
			s["wos"].add(p.facilities_work_order)

	total_spend = sum(v["spend"] for v in vendors.values())
	data = [{
		"vendor": k, "active_contracts": v["active"], "contract_value": v["value"], "expiring_soon": v["expiring"],
		"expired_contracts": v["expired"], "covered_assets": v["assets"], "po_count": v["pos"],
		"fulfilment_pct": pct(v["received"], v["pos"]), "po_spend": v["spend"], "spend_share_pct": pct(v["spend"], total_spend),
		"work_orders_supported": len(v["wos"]),
	} for k, v in vendors.items()]
	data.sort(key=lambda d: -(d["po_spend"] + d["contract_value"]))
	summary = [
		summary_card(_("Vendors"), len(data)),
		summary_card(_("Active Contract Value"), sum(d["contract_value"] for d in data), "Currency"),
		summary_card(_("PO Spend (period)"), total_spend, "Currency"),
		summary_card(_("Contracts Expiring Soon"), sum(d["expiring_soon"] for d in data), indicator="Orange"),
		summary_card(_("Expired Contracts"), sum(d["expired_contracts"] for d in data), indicator="Red"),
	]
	top = data[:12]
	chart = {
		"data": {"labels": [d["vendor"] for d in top], "datasets": [
			{"name": _("PO Spend"), "values": [d["po_spend"] for d in top]},
			{"name": _("Active Contract Value"), "values": [d["contract_value"] for d in top]},
		]},
		"type": "bar",
	}
	columns = [
		{"label": _("Vendor"), "fieldname": "vendor", "fieldtype": "Link", "options": "Supplier", "width": 190},
		{"label": _("Active Contracts"), "fieldname": "active_contracts", "fieldtype": "Int", "width": 120},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 130},
		{"label": _("Expiring Soon"), "fieldname": "expiring_soon", "fieldtype": "Int", "width": 110},
		{"label": _("Expired"), "fieldname": "expired_contracts", "fieldtype": "Int", "width": 80},
		{"label": _("Covered Assets"), "fieldname": "covered_assets", "fieldtype": "Int", "width": 110},
		{"label": _("Purchase Orders"), "fieldname": "po_count", "fieldtype": "Int", "width": 120},
		{"label": _("Fulfilment %"), "fieldname": "fulfilment_pct", "fieldtype": "Percent", "width": 100},
		{"label": _("PO Spend"), "fieldname": "po_spend", "fieldtype": "Currency", "width": 130},
		{"label": _("Spend Share %"), "fieldname": "spend_share_pct", "fieldtype": "Percent", "width": 110},
		{"label": _("Work Orders Supported"), "fieldname": "work_orders_supported", "fieldtype": "Int", "width": 150},
	]
	return columns, data, None, chart, summary
