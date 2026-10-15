# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_settings():
	return frappe.get_cached_doc("Facilities Settings")


def flag_enabled(settings, fieldname):
	"""True when a Check on Facilities Settings is on.

	A Single that was saved before the field existed returns None for it, so
	None is treated as "on" - the new alerts default to enabled after upgrade.
	"""
	value = settings.get(fieldname)
	return value is None or bool(value)


def get_role_emails(role):
	"""Emails of enabled users holding `role` (Administrator/Guest excluded)."""
	users = frappe.get_all(
		"Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"
	)
	if not users:
		return []
	emails = frappe.get_all(
		"User",
		filters={"name": ["in", users], "enabled": 1, "user_type": "System User"},
		pluck="email",
	)
	return sorted({e for e in emails if e and e not in ("admin@example.com",)})


def notify_work_order_status_change(doc):
	"""Notify the relevant person by email/SMS when a Facilities Work Order status changes."""
	settings = get_settings()

	recipient_user = None
	subject = None

	if doc.status == "Pending Approval" and doc.approver:
		recipient_user = doc.approver
		subject = _("Facilities Work Order {0} needs your approval").format(doc.name)
	elif doc.status == "Assigned" and doc.assigned_to:
		recipient_user = doc.assigned_to
		subject = _("Facilities Work Order {0} has been assigned to you").format(doc.name)
	elif doc.status in ("Approved", "In Progress", "Completed", "Closed", "Rejected") and (
		doc.requested_by or doc.raised_by
	):
		# External requesters (email / WhatsApp / web) have no User record, so
		# fall back to the address the ticket was raised with.
		recipient_user = doc.requested_by or doc.raised_by
		subject = _("Facilities Work Order {0} is now {1}").format(doc.name, doc.status)

	if not recipient_user:
		return

	message = _("Work Order: {0}<br>Subject: {1}<br>Status: {2}<br>Priority: {3}").format(
		doc.name, doc.subject, doc.status, doc.priority
	)
	if doc.client_type == "External" or not frappe.db.exists("User", recipient_user):
		from facilities_management.utils.tracking import get_tracking_url

		tracking_url = get_tracking_url(doc.name)
		message += _("<br><br>Track this ticket any time: <a href=\"{0}\">{0}</a>").format(tracking_url)

	if settings.enable_email_notifications:
		_send_email(
			recipient_user, subject, message, reference_doctype=doc.doctype, reference_name=doc.name
		)

	if settings.enable_sms_notifications and frappe.db.exists("User", recipient_user):
		_send_sms(recipient_user, f"{subject}: {doc.name} ({doc.status})")

	if settings.enable_whatsapp_intake and doc.source == "WhatsApp" and doc.raised_by:
		from facilities_management.utils.whatsapp import send_whatsapp_message

		send_whatsapp_message(doc.raised_by, f"{subject}: {doc.name} is now {doc.status}.")


def _send_email(user, subject, message, reference_doctype=None, reference_name=None):
	"""`user` may be a User name or a bare email address (external requester)."""
	email = frappe.db.get_value("User", user, "email")
	if not email and user and "@" in user:
		email = user
	if not email:
		return
	try:
		frappe.sendmail(
			recipients=[email],
			subject=subject,
			message=message,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
	except Exception:
		frappe.log_error(title="Facilities: email notification failed")


def _send_sms(user, message):
	"""Send an SMS via the gateway configured in Facilities Settings.

	This is deliberately gateway-agnostic (mirrors the pattern used for the
	M-Pesa Daraja integration elsewhere): swap out the request body/URL for
	whichever SMS provider is actually contracted, without touching callers.
	"""
	mobile_no = frappe.db.get_value("User", user, "mobile_no")
	if not mobile_no:
		return

	settings = get_settings()
	if not (settings.sms_api_url):
		frappe.log_error(title="Facilities: SMS enabled but no gateway configured")
		return

	try:
		import requests

		api_key = settings.get_password("sms_api_key", raise_exception=False)
		payload = {
			"username": settings.sms_api_username,
			"to": mobile_no,
			"message": message,
			"from": settings.sms_sender_id,
		}
		headers = {"apikey": api_key} if api_key else {}
		requests.post(settings.sms_api_url, data=payload, headers=headers, timeout=10)
	except Exception:
		frappe.log_error(title="Facilities: SMS notification failed")
