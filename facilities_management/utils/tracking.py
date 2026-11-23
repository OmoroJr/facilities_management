# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_url

WO = "Facilities Work Order"
TICKET = "Facilities Ticket"
TICKET_PREFIX = "TKT-"

WO_FIELDS = [
	"name", "subject", "work_order_type", "status", "priority", "creation", "modified",
	"sla_due_date", "started_on", "completed_on", "closed_on", "resolution_notes",
]
TICKET_FIELDS = [
	"name", "subject", "category", "status", "priority", "creation", "modified",
	"resolution_due", "resolved_on", "closed_on", "resolution_notes",
]
# Kept for anything that imports it.
TRACKABLE_FIELDS = WO_FIELDS

CLOSED_STATUSES = ("Completed", "Closed", "Resolved")

# How many lookup attempts a single IP may make in the window below before
# being told to slow down. This is deliberately generous (typos happen) but
# stops a script from enumerating ticket IDs against guessed contacts.
RATE_LIMIT_ATTEMPTS = 15
RATE_LIMIT_WINDOW_SECONDS = 300


@frappe.whitelist(allow_guest=True)
def get_ticket_status(ticket_id, contact):
	"""Look up a Facilities Ticket (TKT-...) or Work Order (WO-...) by ID + the
	email/phone it was raised with. No login required - this is the public
	"track my ticket" lookup.
	"""
	_enforce_rate_limit()

	ticket_id = (ticket_id or "").strip().upper()
	contact = (contact or "").strip().lower()
	if not ticket_id or not contact:
		frappe.throw(_("Please enter both a ticket ID and the email or phone you raised it with."))

	is_ticket = ticket_id.startswith(TICKET_PREFIX)
	doctype = TICKET if is_ticket else WO
	fields = (TICKET_FIELDS if is_ticket else WO_FIELDS) + ["raised_by", "requested_by"]
	doc = frappe.db.get_value(doctype, ticket_id, fields, as_dict=True)

	# Same generic error whether the ticket doesn't exist or the contact
	# doesn't match it, so this endpoint can't be used to enumerate tickets.
	if not doc or not _contact_matches(doc, contact):
		frappe.throw(_("We couldn't find a ticket with that ID and contact combination."))

	if is_ticket:
		result = {
			"name": doc.name, "subject": doc.subject, "work_order_type": doc.category,
			"status": doc.status, "priority": doc.priority, "creation": doc.creation,
			"modified": doc.modified, "sla_due_date": doc.resolution_due, "started_on": None,
			"completed_on": doc.resolved_on, "closed_on": doc.closed_on,
			"resolution_notes": doc.resolution_notes,
		}
	else:
		result = {field: doc.get(field) for field in WO_FIELDS}
	if doc.status not in CLOSED_STATUSES:
		result["resolution_notes"] = None
	return result


def get_tracking_url(ticket_name):
	"""Absolute link to the public tracking page, pre-filled with the ticket ID."""
	return get_url(f"/track-ticket?ticket={ticket_name}")


def _contact_matches(doc, contact):
	candidates = set()
	if doc.raised_by:
		raised_by = doc.raised_by.strip().lower()
		candidates.add(raised_by)
		if "@" not in raised_by:  # a phone number (WhatsApp / phone intake)
			candidates.add(_digits_only(raised_by))
	if doc.requested_by:
		user_email = frappe.db.get_value("User", doc.requested_by, "email")
		if user_email:
			candidates.add(user_email.strip().lower())

	contact_digits = _digits_only(contact)
	return contact in candidates or bool(contact_digits and contact_digits in candidates)


def _digits_only(value):
	return "".join(ch for ch in (value or "") if ch.isdigit())


def _enforce_rate_limit():
	ip = frappe.local.request_ip or "unknown"
	key = f"facilities_ticket_tracking:{ip}"
	cache = frappe.cache()
	count = frappe.utils.cint(cache.get_value(key)) or 0
	if count >= RATE_LIMIT_ATTEMPTS:
		frappe.throw(_("Too many attempts. Please try again in a few minutes."))
	cache.set_value(key, count + 1, expires_in_sec=RATE_LIMIT_WINDOW_SECONDS)
