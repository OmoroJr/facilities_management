# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, now_datetime, add_days, time_diff_in_hours


def generate_due_preventive_maintenance():
	"""Daily job: create Facilities Work Orders for any due Preventive Maintenance Schedule."""
	due = frappe.get_all(
		"Preventive Maintenance Schedule",
		filters={"status": "Active", "next_due_date": ["<=", today()]},
		pluck="name",
	)
	for name in due:
		schedule = frappe.get_doc("Preventive Maintenance Schedule", name)
		try:
			schedule.generate_work_order()
		except Exception:
			frappe.log_error(title=f"Facilities: failed to generate PM work order for {name}")


def check_contract_renewals():
	"""Daily job: flag Facilities Maintenance Contracts approaching expiry."""
	contracts = frappe.get_all(
		"Facilities Maintenance Contract",
		filters={"status": "Active"},
		fields=["name", "end_date", "renewal_reminder_days", "contract_title"],
	)
	for c in contracts:
		if not c.end_date:
			continue
		days_left = (getdate(c.end_date) - getdate(today())).days
		if days_left < 0:
			frappe.db.set_value("Facilities Maintenance Contract", c.name, "status", "Expired")
		elif days_left <= (c.renewal_reminder_days or 30):
			frappe.db.set_value("Facilities Maintenance Contract", c.name, "status", "Pending Renewal")
			_notify_role(
				"Facilities Manager",
				_("Contract renewal due: {0}").format(c.contract_title or c.name),
				_("Facilities Maintenance Contract {0} expires on {1} ({2} day(s) left).").format(
					c.name, c.end_date, days_left
				),
			)


def check_certification_expiries():
	"""Daily job: notify when Safety Inspection certifications are about to expire."""
	upcoming = frappe.get_all(
		"Safety Inspection",
		filters={"certification_expiry": ["between", [today(), add_days(today(), 30)]]},
		fields=["name", "inspection_type", "certification_expiry", "facility_asset"],
	)
	for insp in upcoming:
		_notify_role(
			"Facilities Manager",
			_("Certification expiring soon: {0}").format(insp.inspection_type),
			_("Safety Inspection {0} ({1}) certification expires on {2}.").format(
				insp.name, insp.facility_asset or "", insp.certification_expiry
			),
		)


def auto_close_completed_work_orders():
	"""Daily job: auto-close work orders that have been Completed for longer than the configured window."""
	settings = frappe.get_cached_doc("Facilities Settings")
	days = settings.auto_close_after_days or 7
	cutoff = add_days(today(), -days)
	stale = frappe.get_all(
		"Facilities Work Order",
		filters={"status": "Completed", "completed_on": ["<=", cutoff]},
		pluck="name",
	)
	for name in stale:
		frappe.db.set_value("Facilities Work Order", name, "status", "Closed")
		frappe.db.set_value("Facilities Work Order", name, "closed_on", now_datetime())


def escalate_unassigned_work_orders():
	"""Hourly job: notify Facilities Manager if an Approved order has sat unassigned too long."""
	settings = frappe.get_cached_doc("Facilities Settings")
	threshold = settings.escalation_hours or 24
	candidates = frappe.get_all(
		"Facilities Work Order",
		filters={"status": "Approved"},
		fields=["name", "subject", "approval_date"],
	)
	for wo in candidates:
		if not wo.approval_date:
			continue
		if time_diff_in_hours(now_datetime(), wo.approval_date) >= threshold:
			_notify_role(
				"Facilities Manager",
				_("Work Order awaiting assignment: {0}").format(wo.name),
				_("Facilities Work Order {0} ({1}) has been approved but unassigned for over {2} hours.").format(
					wo.name, wo.subject, threshold
				),
			)


def notify_sla_breaches():
	"""Hourly job: alert once when an open Work Order passes its SLA due date."""
	from facilities_management.utils.notifications import flag_enabled, get_settings

	if not flag_enabled(get_settings(), "email_notify_sla_breach"):
		return

	overdue = frappe.get_all(
		"Facilities Work Order",
		filters={
			"status": ["in", ["Submitted", "Pending Approval", "Approved", "Assigned", "In Progress", "On Hold"]],
			"sla_due_date": ["<", now_datetime()],
			"sla_breach_notified": 0,
		},
		fields=["name", "subject", "priority", "sla_due_date", "assigned_to"],
	)
	for wo in overdue:
		_notify_role(
			"Facilities Manager",
			_("SLA breached: Work Order {0}").format(wo.name),
			_("Facilities Work Order {0} ({1}, {2} priority) passed its SLA due date of {3}.").format(
				wo.name, wo.subject, wo.priority, wo.sla_due_date
			),
			extra_users=[wo.assigned_to] if wo.assigned_to else None,
			reference_doctype="Facilities Work Order",
			reference_name=wo.name,
		)
		frappe.db.set_value(
			"Facilities Work Order", wo.name, "sla_breach_notified", 1, update_modified=False
		)


def _notify_role(role, subject, message, extra_users=None, reference_doctype=None, reference_name=None):
	from facilities_management.utils.notifications import get_role_emails

	settings = frappe.get_cached_doc("Facilities Settings")
	if not settings.enable_email_notifications:
		return
	emails = set(get_role_emails(role))
	for user in extra_users or []:
		email = frappe.db.get_value("User", user, "email")
		if email:
			emails.add(email)
	if emails:
		try:
			frappe.sendmail(
				recipients=sorted(emails),
				subject=subject,
				message=message,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)
		except Exception:
			frappe.log_error(title="Facilities: role notification failed")
