# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe


def on_communication_insert(doc, method=None):
	"""Fires after any Communication is inserted (see hooks.py doc_events).

	When the Communication is an inbound email against a Facilities Work
	Order (created automatically by Frappe's `email_append_to` mechanism),
	fill in the fields that mechanism does not set on its own: who raised
	it, whether they're internal or external, and the request body.
	"""
	if doc.reference_doctype != "Facilities Work Order" or not doc.reference_name:
		return
	if doc.communication_type != "Communication":
		return
	if doc.sent_or_received != "Received":
		return

	# Only enrich on the *founding* email - the one Frappe's email_append_to
	# mechanism just used to create this ticket (it already ran and set
	# raised_by/subject on the doc before this Communication was inserted,
	# so we can't tell "founding" from "reply" by checking wo.raised_by).
	# Count received Communications instead: exactly one means this is it.
	received_count = frappe.db.count(
		"Communication",
		{
			"reference_doctype": "Facilities Work Order",
			"reference_name": doc.reference_name,
			"sent_or_received": "Received",
		},
	)
	if received_count != 1:
		return

	wo = frappe.get_doc("Facilities Work Order", doc.reference_name)
	sender_email = (doc.sender or "").strip()
	updates = {"source": "Email", "raised_by": sender_email}

	system_user = frappe.db.get_value("User", {"email": sender_email}, "name")
	if system_user:
		updates["requested_by"] = system_user
		updates["client_type"] = "Internal"
	else:
		# clear the field-level default("user") that email_append_to would
		# otherwise have stamped with the background worker's user
		updates["requested_by"] = None
		updates["client_type"] = "External"
		updates["external_client_name"] = doc.sender_full_name or sender_email

	if not wo.description:
		updates["description"] = doc.content

	wo.db_set(updates, notify=False)

	# email_append_to inserts straight into Draft with no human present to
	# press "Submit" - move it into the approval queue automatically.
	if wo.status == "Draft":
		wo.db_set("status", "Submitted", notify=False)
