# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, today

from facilities_management.utils.report_helpers import WO, summary_card

REPEAT_THRESHOLD = 3  # corrective tickets in 12 months


def execute(filters=None):
	filters = frappe._dict(filters or {})
	cond = {}
	for key in ("asset_category", "status", "criticality", "department", "vendor"):
		if filters.get(key):
			cond[key] = filters[key]
	assets = frappe.get_all(
		"Facility Asset", filters=cond,
		fields=["name", "asset_name", "asset_code", "asset_category", "status", "criticality", "department",
				"building", "purchase_date", "purchase_cost", "warranty_expiry", "last_serviced_on", "vendor"],
	)
	names = [a.name for a in assets]
	corrective, next_pm = {}, {}
	if names:
		for r in frappe.get_all(
			WO, filters={"facility_asset": ["in", names], "work_order_type": "Corrective",
						 "creation": [">=", add_days(today(), -365)], "status": ["!=", "Cancelled"]},
			fields=["facility_asset", "count(name) as n"], group_by="facility_asset",
		):
			corrective[r.facility_asset] = r.n
		for r in frappe.get_all(
			"Preventive Maintenance Schedule", filters={"facility_asset": ["in", names], "status": "Active"},
			fields=["facility_asset", "min(next_due_date) as due"], group_by="facility_asset",
		):
			next_pm[r.facility_asset] = r.due

	t = today()
	data, counts = [], {"Under Warranty": 0, "Expiring (90 days)": 0, "Expired": 0, "No Warranty Info": 0}
	value = repeat = 0
	for a in assets:
		if a.warranty_expiry:
			days_left = date_diff(a.warranty_expiry, t)
			state = "Expired" if days_left < 0 else "Expiring (90 days)" if days_left <= 90 else "Under Warranty"
		else:
			days_left, state = None, "No Warranty Info"
		if filters.get("warranty_state") and filters["warranty_state"] != state:
			continue
		n = corrective.get(a.name, 0)
		is_repeat = n >= REPEAT_THRESHOLD
		counts[state] += 1
		value += a.purchase_cost or 0
		repeat += 1 if is_repeat else 0
		data.append({
			**a,
			"age_years": round(date_diff(t, a.purchase_date) / 365.25, 1) if a.purchase_date else None,
			"warranty_days_left": days_left, "warranty_state": state,
			"days_since_service": date_diff(t, a.last_serviced_on) if a.last_serviced_on else None,
			"next_pm_due": next_pm.get(a.name), "corrective_12m": n,
			"repeat_failure": _("Yes") if is_repeat else "",
		})
	data.sort(key=lambda d: (d["warranty_days_left"] is None, d["warranty_days_left"] if d["warranty_days_left"] is not None else 0))

	summary = [
		summary_card(_("Assets"), len(data)),
		summary_card(_("Total Purchase Value"), value, "Currency"),
		summary_card(_("Warranty Expiring (90d)"), counts["Expiring (90 days)"], indicator="Orange" if counts["Expiring (90 days)"] else "Green"),
		summary_card(_("Warranty Expired"), counts["Expired"], indicator="Red" if counts["Expired"] else "Green"),
		summary_card(_("Repeat-Failure Assets"), repeat, indicator="Red" if repeat else "Green"),
	]
	chart = {
		"data": {"labels": list(counts), "datasets": [{"name": _("Assets"), "values": list(counts.values())}]},
		"type": "donut", "colors": ["#29A745", "#F5A623", "#E24C4C", "#9AA0A6"],
	}
	return get_columns(), data, None, chart, summary


def get_columns():
	return [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Facility Asset", "width": 120},
		{"label": _("Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
		{"label": _("Code"), "fieldname": "asset_code", "fieldtype": "Data", "width": 100},
		{"label": _("Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Criticality"), "fieldname": "criticality", "fieldtype": "Data", "width": 90},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
		{"label": _("Building"), "fieldname": "building", "fieldtype": "Data", "width": 100},
		{"label": _("Age (yrs)"), "fieldname": "age_years", "fieldtype": "Float", "precision": 1, "width": 80},
		{"label": _("Purchase Cost"), "fieldname": "purchase_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Warranty Expiry"), "fieldname": "warranty_expiry", "fieldtype": "Date", "width": 110},
		{"label": _("Warranty Days Left"), "fieldname": "warranty_days_left", "fieldtype": "Int", "width": 120},
		{"label": _("Warranty State"), "fieldname": "warranty_state", "fieldtype": "Data", "width": 130},
		{"label": _("Last Serviced"), "fieldname": "last_serviced_on", "fieldtype": "Date", "width": 100},
		{"label": _("Days Since Service"), "fieldname": "days_since_service", "fieldtype": "Int", "width": 120},
		{"label": _("Next PM Due"), "fieldname": "next_pm_due", "fieldtype": "Date", "width": 100},
		{"label": _("Corrective (12m)"), "fieldname": "corrective_12m", "fieldtype": "Int", "width": 110},
		{"label": _("Repeat Failure"), "fieldname": "repeat_failure", "fieldtype": "Data", "width": 100},
	]
