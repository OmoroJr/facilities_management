# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, nowdate

from facilities_management.utils.ntsa import COMPLIANCE_ITEMS, compute_status, get_soon_days


def execute(filters=None):
	"""One row per vehicle per thing it must keep valid: NTSA inspection, insurance, speed governor."""
	filters = frappe._dict(filters or {})
	cond = {"vehicle_type": filters.vehicle_type} if filters.get("vehicle_type") else {}
	fields = ["name", "registration_number", "vehicle_name", "vehicle_type", "driver", "insurance_provider",
			  "insurance_policy_number", "governor_certificate_number", "ntsa_certificate_number"]
	fields += [f for item in COMPLIANCE_ITEMS for f in item[1:3]]
	soon = get_soon_days()
	reference = {"NTSA Inspection": "ntsa_certificate_number", "Insurance": "insurance_policy_number", "Speed Governor": "governor_certificate_number"}

	data = []
	for v in frappe.get_all("Facility Vehicle", filters=cond, fields=fields):
		for label, required, expiry, _status in COMPLIANCE_ITEMS:
			if filters.get("item") and filters.item != label:
				continue
			if not v.get(required):
				continue
			status = compute_status(v.get(required), v.get(expiry), soon)
			if filters.get("status") and status != filters.status:
				continue
			due = v.get(expiry)
			data.append({
				"vehicle": v.name, "registration_number": v.registration_number, "vehicle_name": v.vehicle_name,
				"vehicle_type": v.vehicle_type, "driver": v.driver, "item": label, "reference": v.get(reference[label]),
				"provider": v.insurance_provider if label == "Insurance" else None, "expiry": due,
				"days_left": date_diff(due, nowdate()) if due else None, "status": status,
			})
	data.sort(key=lambda r: (r["days_left"] is None, r["days_left"] if r["days_left"] is not None else 0))

	columns = [
		{"fieldname": "registration_number", "label": _("Registration"), "fieldtype": "Link", "options": "Facility Vehicle", "width": 120},
		{"fieldname": "vehicle_name", "label": _("Vehicle"), "fieldtype": "Data", "width": 140},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Employee", "width": 130},
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Data", "width": 130},
		{"fieldname": "reference", "label": _("Policy / Certificate"), "fieldtype": "Data", "width": 150},
		{"fieldname": "provider", "label": _("Insurer"), "fieldtype": "Data", "width": 130},
		{"fieldname": "expiry", "label": _("Expires"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_left", "label": _("Days Left"), "fieldtype": "Int", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
	]
	counts = {}
	for row in data:
		counts[row["status"]] = counts.get(row["status"], 0) + 1
	chart = {"data": {"labels": list(counts), "datasets": [{"values": list(counts.values())}]}, "type": "donut"}
	return columns, data, None, chart
