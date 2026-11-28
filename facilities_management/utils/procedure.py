# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""ABS Work Order Procedure Manual support: cost policy data and the acknowledgement job."""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, now_datetime

WO = "Facilities Work Order"

# ABS Facilities and Department-Specific Cost Management Policy (updated 15 December 2025).
COST_POLICY_ITEMS = (
	('Windows, doors, roofs and floors', 'General Facilities Cost', '2.1', 'Facilities'),
	('Perimeter walls and fencing', 'General Facilities Cost', '2.1', 'Facilities'),
	('Drainage and sewer systems', 'General Facilities Cost', '2.1', 'Facilities'),
	('Water storage tanks', 'General Facilities Cost', '2.1', 'Facilities'),
	('Water supply systems', 'General Facilities Cost', '2.2', 'Facilities'),
	('Electricity and power distribution', 'General Facilities Cost', '2.2', 'Facilities'),
	('Telecommunication systems (PBX, fixed lines)', 'General Facilities Cost', '2.2', 'Facilities'),
	('General grounds maintenance, gardening and landscaping', 'General Facilities Cost', '2.3', 'Facilities'),
	('Lawn mowers and grounds equipment', 'General Facilities Cost', '2.4', 'Facilities'),
	('Shared photocopiers, printers, laminators, shredders and paper cutters', 'General Facilities Cost', '2.5', 'Facilities'),
	('Common-area appliances (refrigerators, water dispensers, microwaves, kettles, toasters)', 'General Facilities Cost', '2.5', 'Facilities'),
	('General stationery', 'General Facilities Cost', '2.6', 'Facilities'),
	('Chai / tea services', 'General Facilities Cost', '2.6', 'Facilities'),
	('Parking fees', 'General Facilities Cost', '2.6', 'Facilities (under review where vehicles are assigned to a department)'),
	('Outsourced guarding services', 'General Facilities Cost', '2.7', 'Facilities'),
	('Fire safety equipment servicing', 'General Facilities Cost', '2.7', 'Facilities'),
	('Alarm systems', 'General Facilities Cost', '2.7', 'Facilities'),
	('CCTV systems', 'General Facilities Cost', '2.7', 'Facilities'),
	('Departmental office and colour printers, shredders', 'Department-Specific Cost', '3.1', 'Requesting department'),
	('Department-owned appliances (microwaves, coffee makers, water dispensers, toasters)', 'Department-Specific Cost', '3.1', 'Requesting department'),
	('Wall hangings and fittings', 'Department-Specific Cost', '3.2', 'Requesting department'),
	('Change of paint colour beyond standard Facilities finishes', 'Department-Specific Cost', '3.2', 'Requesting department'),
	('Office reorganization (partitioning, layout changes)', 'Department-Specific Cost', '3.2', 'Requesting department'),
	('Department-specific security enhancements', 'Department-Specific Cost', '3.2', 'Requesting department'),
	('Stationery unique to departmental operations', 'Department-Specific Cost', '3.3', 'Requesting department'),
	('Damage clearly caused by a department or its staff', 'Department-Specific Cost', '3.4', 'Responsible department'),
	('Repairs from misuse, negligence or unauthorized modifications', 'Department-Specific Cost', '3.4', 'Responsible department'),
	('Modifications from donations or a change in operational use of a space', 'Department-Specific Cost', '3.5', 'Requesting department'),
	('Washing machines (AIM Air, AIM Care)', 'Department-Specific Cost', '3.6', 'Owning department'),
	('Water filters and refrigerators (AIM Air)', 'Department-Specific Cost', '3.6', 'AIM Air'),
	('Playground equipment at the Tumaini parking lot', 'Department-Specific Cost', '3.6', 'Owning department'),
	('Additional security where basic security exists (Finance cash office access control, radio base auxiliary door)', 'Department-Specific Cost', '3.7', 'Requesting department'),
	('Extra or deep cleaning beyond standard Facilities provision', 'Department-Specific Cost', '3.7', 'Requesting department'),
	('Convenience items (kettles, coffee makers, toasters, water dispensers, microwaves) and refreshments', 'Department-Specific Cost', '3.8', 'Requesting department; follows the standard work order process'),
	('Office space', 'Shared / Exceptional Area', '4.1', 'Shared by prior agreement'),
	('Conference and meeting rooms (AC Conference Room: AIM Care; AA Conference Room: AIM Air; Facilities/Finance Meeting Room: Facilities)', 'Shared / Exceptional Area', '4.1', 'Managing department; AIM Care and AIM Air have first priority for their main rooms'),
	('AIM Care kitchen and kitchen equipment', 'Shared / Exceptional Area', '4.2', 'Shared by prior agreement'),
	('Gym', 'Shared / Exceptional Area', '4.2', 'Shared by all departments on breakdown'),
	('Generator (AA generator maintained by Facilities, fuel provided by GCP)', 'Shared / Exceptional Area', '4.2', 'Facilities and GCP'),
	('Pavilion', 'Shared / Exceptional Area', '4.3', 'Shared; AIM Care has first priority of use'),
	('Playground (near apartments)', 'Shared / Exceptional Area', '4.3', 'Shared by prior agreement'),
	('Facilities vehicles (shared)', 'Vehicle', 'Procedure 2.7(d)', 'Facilities'),
	('AIM Air vehicles (tractor, forklift)', 'Vehicle', 'Procedure 2.7(d)', 'AIM Air'),
	('Fire', 'Emergency', '5', 'Exceptional circumstances'),
	('Flooding and water shortage', 'Emergency', '5', 'Exceptional circumstances'),
	('Sewer blockage', 'Emergency', '5', 'Exceptional circumstances'),
	('Power outage / failure', 'Emergency', '5', 'Exceptional circumstances'),
	('Natural calamities (floods, tremors, storms)', 'Emergency', '5', 'Exceptional circumstances'),
	('Accidents', 'Emergency', '5', 'Exceptional circumstances'),
	('Unnatural animal infestations', 'Emergency', '5', 'Exceptional circumstances'),
	('Government policy changes (asbestos removal, pit latrine decommissioning, waste segregation)', 'Emergency', '5', 'Exceptional circumstances'),
)


def ensure_cost_policy_items():
	"""Idempotent: add the policy items that are missing, leave edited ones alone."""
	for name, category, reference, responsible in COST_POLICY_ITEMS:
		if not frappe.db.exists("Facilities Cost Policy Item", name):
			frappe.get_doc({
				"doctype": "Facilities Cost Policy Item", "item_name": name, "cost_category": category,
				"policy_reference": reference, "responsible": responsible, "is_active": 1,
			}).insert(ignore_permissions=True)


def check_acknowledgement_overdue():
	"""Hourly: step 4 says Facilities must acknowledge a submitted work order within 24 hours."""
	from facilities_management.utils.scheduler import _notify_role

	settings = frappe.get_cached_doc("Facilities Settings")
	hours = settings.acknowledgement_hours or 24
	now = now_datetime()
	rows = frappe.get_all(
		WO,
		filters={
			"status": "Submitted", "acknowledged_on": ["is", "not set"], "ack_breach_notified": 0,
			"creation": ["between", [add_days(now, -30), add_to_date(now, hours=-hours)]],
		},
		fields=["name", "subject", "creation", "department"],
	)
	for wo in rows:
		_notify_role(
			"Facilities Manager",
			_("Not acknowledged within {0} hours: {1}").format(hours, wo.name),
			_("Work order {0} ({1}) was submitted on {2} and has not been acknowledged.").format(wo.name, wo.subject, wo.creation),
			reference_doctype=WO, reference_name=wo.name,
		)
		frappe.db.set_value(WO, wo.name, "ack_breach_notified", 1, update_modified=False)
