# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt
#
# Meta WhatsApp Cloud API integration (no third-party app required).
#
# Setup on Meta's side (WhatsApp > Configuration, in the Meta App dashboard):
#   Webhook URL     : https://<your-site>/api/method/facilities_management.utils.whatsapp.webhook
#   Verify Token    : must match "Webhook Verify Token" in Facilities Settings
#   Subscribe to    : "messages" field
#
# Fill in Facilities Settings: Phone Number ID, Cloud API Access Token
# (a permanent token from a System User / WhatsApp Business app), and tick
# "Enable WhatsApp Request Intake".

import json
import re

import frappe
from frappe import _


def get_settings():
	return frappe.get_cached_doc("Facilities Settings")


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def webhook():
	"""Single endpoint Meta calls both to verify the webhook (GET) and to
	deliver message events (POST)."""
	if frappe.request.method == "GET":
		return _verify()
	return _handle_event()


def _verify():
	settings = get_settings()
	args = frappe.local.form_dict
	mode = args.get("hub.mode")
	token = args.get("hub.verify_token")
	challenge = args.get("hub.challenge")

	if mode == "subscribe" and token and settings.whatsapp_verify_token and token == settings.whatsapp_verify_token:
		frappe.response["type"] = "page"
		frappe.response["page_body"] = challenge or ""
		return

	frappe.local.response["http_status_code"] = 403
	frappe.response["type"] = "page"
	frappe.response["page_body"] = "Verification failed"


def _handle_event():
	settings = get_settings()
	if not settings.enable_whatsapp_intake:
		return {"status": "ignored"}

	try:
		payload = json.loads(frappe.request.data)
	except Exception:
		frappe.log_error(title="Facilities WhatsApp: bad payload")
		return {"status": "ignored"}

	for entry in payload.get("entry", []):
		for change in entry.get("changes", []):
			value = change.get("value", {})
			for message in value.get("messages", []):
				_process_message(message, settings)

	# Always 200 back to Meta quickly, regardless of internal outcome,
	# so it doesn't keep retrying the same event.
	return {"status": "received"}


def _process_message(message, settings):
	wa_message_id = message.get("id")
	if not wa_message_id:
		return
	if frappe.db.exists("WhatsApp Message Log", {"wa_message_id": wa_message_id}):
		return  # already processed (Meta redelivers on timeout)

	from_number = message.get("from")
	text = ""
	if message.get("type") == "text":
		text = (message.get("text") or {}).get("body", "")
	else:
		text = f"[{message.get('type', 'unsupported')} message - please see WhatsApp for details]"

	wo_name = None
	try:
		wo_name = _create_work_order(from_number, text)
	except Exception:
		frappe.log_error(title="Facilities WhatsApp: failed to create work order")

	frappe.get_doc({
		"doctype": "WhatsApp Message Log",
		"wa_message_id": wa_message_id,
		"from_number": from_number,
		"message_body": text,
		"facilities_work_order": wo_name,
	}).insert(ignore_permissions=True)

	if wo_name and settings.whatsapp_send_acknowledgement:
		send_whatsapp_message(
			from_number,
			_("Thanks - we've logged your request as {0}. We'll update you here once it's assigned.").format(wo_name),
		)


def _create_work_order(from_number, text):
	subject = (text or "").strip().splitlines()[0][:120] if text else f"WhatsApp request from {from_number}"
	if not subject:
		subject = f"WhatsApp request from {from_number}"

	employee = _find_employee_by_phone(from_number)

	wo = frappe.new_doc("Facilities Work Order")
	wo.subject = subject
	wo.description = text
	wo.source = "WhatsApp"
	wo.raised_by = from_number
	wo.work_order_type = "Request"
	wo.priority = "Medium"

	if employee:
		wo.client_type = "Internal"
		wo.department = employee.get("department")
		if employee.get("user_id"):
			wo.requested_by = employee.get("user_id")
	else:
		# clear the field-level default("user") - this doc is being created
		# from a guest webhook request, not by the reporter themselves
		wo.requested_by = None
		wo.client_type = "External"
		wo.external_client_name = from_number

	wo.insert(ignore_permissions=True)
	return wo.name


def _normalize_phone(number):
	"""Keep only digits, and compare on the last 9 (drops leading 0 / country code differences)."""
	digits = re.sub(r"\D", "", number or "")
	return digits[-9:] if len(digits) >= 9 else digits


def _find_employee_by_phone(from_number):
	target = _normalize_phone(from_number)
	if not target:
		return None
	candidates = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "cell_number", "department", "user_id"],
	)
	for c in candidates:
		if _normalize_phone(c.cell_number) == target:
			return c
	return None


def send_whatsapp_message(to_number, message):
	"""Send a plain-text WhatsApp message via the Cloud API.

	Note: outside Meta's 24-hour customer-service window, free-form text
	messages are rejected by the API and a pre-approved template message
	must be used instead - this helper only covers the free-form case
	(acknowledgements and quick status updates sent soon after contact).
	"""
	settings = get_settings()
	if not (settings.enable_whatsapp_intake and settings.whatsapp_phone_number_id):
		return

	try:
		import requests

		token = settings.get_password("whatsapp_access_token", raise_exception=False)
		if not token:
			return

		url = (
			f"https://graph.facebook.com/{settings.whatsapp_api_version or 'v20.0'}/"
			f"{settings.whatsapp_phone_number_id}/messages"
		)
		headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
		body = {
			"messaging_product": "whatsapp",
			"to": to_number,
			"type": "text",
			"text": {"body": message},
		}
		requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
	except Exception:
		frappe.log_error(title="Facilities WhatsApp: send failed")
