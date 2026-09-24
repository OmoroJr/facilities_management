# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_url

TRACKABLE_FIELDS = [
	"name", "subject", "work_order_type", "status", "priority",
	"creation", "modified", "sla_due_date", "started_on",
	"completed_on", "closed_on", "resolution_notes",
]

CLOSED_STATUSES = ("Completed", "Closed")

# How many lookup attempts a single IP may make in the window below before
# being told to slow down. This is deliberately generous (typos happen) but
# stops a script from enumerating WO-YYYY-##### against guessed contacts.
RATE_LIMIT_ATTEMPTS = 15
RATE_LIMIT_WINDOW_SECONDS = 300


@frappe.whitelist(allow_guest=True)
def get_ticket_status(ticket_id, contact):
	"""Look up a Facilities Work Order by ID + the email/phone it was raised
	with. No login required - this is the public "track my ticket" lookup.
	"""
	_enforce_rate_limit()

	ticket_id = (ticket_id or "").strip()
	contact = (contact or "").strip().lower()
	if not ticket_id or not contact:
		frappe.throw(_("Please enter both a ticket ID and the email or phone you raised it with."))

	doc = frappe.db.get_value(
		"Facilities Work Order",
		ticket_id,
		TRACKABLE_FIELDS + ["raised_by", "whatsapp_number", "requested_by"],
		as_dict=True,
	)

	# Same generic error whether the ticket doesn't exist or the contact
	# doesn't match it, so this endpoint can't be used to enumerate tickets.
	if not doc or not _contact_matches(doc, contact):
		frappe.throw(_("We couldn't find a ticket with that ID and contact combination."))

	result = {field: doc.get(field) for field in TRACKABLE_FIELDS}
	if doc.status not in CLOSED_STATUSES:
		result["resolution_notes"] = None
	return result


def get_tracking_url(ticket_name):
	"""Absolute link to the public tracking page, pre-filled with the ticket ID."""
	return get_url(f"/track-ticket?ticket={ticket_name}")


def _contact_matches(doc, contact):
	candidates = set()
	if doc.raised_by:
		candidates.add(doc.raised_by.strip().lower())
	if doc.whatsapp_number:
		candidates.add(_digits_only(doc.whatsapp_number))
	if doc.requested_by:
		user_email = frappe.db.get_value("User", doc.requested_by, "email")
		if user_email:
			candidates.add(user_email.strip().lower())

	contact_digits = _digits_only(contact)
	return contact in candidates or (contact_digits and contact_digits in candidates)


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
