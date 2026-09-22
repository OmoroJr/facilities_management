# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_settings():
	return frappe.get_cached_doc("Facilities Settings")


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
	elif doc.status in ("Completed", "Closed", "Rejected") and doc.requested_by:
		recipient_user = doc.requested_by
		subject = _("Facilities Work Order {0} is now {1}").format(doc.name, doc.status)

	if not recipient_user:
		return

	message = _("Work Order: {0}<br>Subject: {1}<br>Status: {2}<br>Priority: {3}").format(
		doc.name, doc.subject, doc.status, doc.priority
	)

	if settings.enable_email_notifications:
		_send_email(recipient_user, subject, message)

	if settings.enable_sms_notifications:
		_send_sms(recipient_user, f"{subject}: {doc.name} ({doc.status})")


def _send_email(user, subject, message):
	email = frappe.db.get_value("User", user, "email")
	if not email:
		return
	try:
		frappe.sendmail(recipients=[email], subject=subject, message=message)
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
