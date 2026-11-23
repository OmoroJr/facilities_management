# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""Ticketing glue for Facilities Ticket.

Wired up in hooks.py:
  Communication.after_insert          -> on_communication_insert
  Facilities Work Order.on_update     -> sync_ticket_from_work_order
  scheduler (hourly / daily)          -> check_ticket_sla, auto_close_resolved_tickets
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_url_to_form, now_datetime, strip_html

from facilities_management.utils.notifications import (
	flag_enabled,
	get_role_emails,
	get_settings,
)

TICKET = "Facilities Ticket"
OPEN_STATUSES = ("Open", "In Progress", "Waiting on Requester")


def _link(name):
	return f'<a href="{get_url_to_form(TICKET, name)}">{name}</a>'


def _user_email(user):
	return frappe.db.get_value("User", user, "email") if user else None


def _requester_address(doc):
	"""Email address (or user id) the requester can be reached on, if any."""
	if doc.raised_by and "@" in doc.raised_by:
		return doc.raised_by
	return doc.requested_by if doc.requested_by and frappe.db.exists("User", doc.requested_by) else None


def _send(recipients, subject, message, ticket_name):
	recipients = sorted({r for r in recipients if r})
	if not recipients:
		return
	try:
		frappe.sendmail(
			recipients=recipients, subject=subject, message=message,
			reference_doctype=TICKET, reference_name=ticket_name,
		)
	except Exception:
		frappe.log_error(title="Facilities: ticket email failed")


# ----------------------------------------------------------------- creation

def notify_ticket_created(doc):
	settings = get_settings()
	if not settings.enable_email_notifications:
		return

	if flag_enabled(settings, "email_notify_new_ticket"):
		recipients = set(get_role_emails("Facilities Manager"))
		recipients.add(_user_email(doc.assigned_to))
		recipients.discard(_user_email(doc.requested_by))
		recipients.discard(doc.raised_by)
		_send(
			recipients,
			_("New Facilities Ticket {0}: {1}").format(doc.name, doc.subject),
			_("A new ticket has been logged.<br><br>Ticket: {0}<br>Subject: {1}<br>Category: {2}<br>"
			  "Priority: {3}<br>Raised by: {4}<br>First response due: {5}").format(
				_link(doc.name), doc.subject, doc.category or "-", doc.priority,
				doc.external_client_name or doc.requested_by or doc.raised_by or "-",
				doc.response_due or "-"),
			doc.name,
		)

	# Tickets created by an inbound email (Frappe sets ignore_mandatory on
	# those) are acknowledged from on_communication_insert instead, once the
	# sender has been identified and the Enable Email Request Intake toggle
	# has been checked.
	if not doc.flags.ignore_mandatory:
		send_acknowledgement(doc)


def send_acknowledgement(doc):
	from facilities_management.utils.tracking import get_tracking_url

	to = _requester_address(doc)
	if not to:
		return
	message = _(
		"Thanks - we've received your request and logged it as <b>{0}</b> (priority: {1}).<br><br>"
		"You can check its progress any time at: <a href=\"{2}\">{2}</a><br>"
		"You'll need this email address and the ticket ID above. You can also just reply to this email "
		"to add information."
	).format(doc.name, doc.priority, get_tracking_url(doc.name))
	_send([to] if "@" in to else [_user_email(to)], _("We've received your request: {0}").format(doc.name),
		  message, doc.name)


# ------------------------------------------------------------------ updates

def notify_ticket_update(doc):
	settings = get_settings()
	before = doc.get_doc_before_save()
	if not before:
		return  # insert: handled by notify_ticket_created

	if settings.enable_email_notifications and doc.assigned_to and doc.assigned_to != before.assigned_to \
			and doc.assigned_to != frappe.session.user:
		_send(
			[_user_email(doc.assigned_to)],
			_("Facilities Ticket {0} has been assigned to you").format(doc.name),
			_("Ticket {0} ({1}) has been assigned to you.<br>Priority: {2}<br>Resolution due: {3}").format(
				_link(doc.name), doc.subject, doc.priority, doc.resolution_due or "-"),
			doc.name,
		)

	if doc.status == before.status or doc.status not in ("Waiting on Requester", "Resolved", "Closed"):
		return

	from facilities_management.utils.tracking import get_tracking_url

	subject = _("Your request {0} is now {1}").format(doc.name, _(doc.status))
	if settings.enable_email_notifications:
		body = _("Ticket: {0}<br>Subject: {1}<br>Status: {2}").format(doc.name, doc.subject, _(doc.status))
		if doc.status == "Resolved" and doc.resolution_notes:
			body += _("<br><br><b>Resolution:</b><br>{0}").format(frappe.utils.escape_html(doc.resolution_notes))
		if doc.status == "Resolved":
			body += _("<br><br>If this has not fixed the problem, just reply to this email and we will reopen it.")
		body += _("<br><br>Track this ticket any time: <a href=\"{0}\">{0}</a>").format(get_tracking_url(doc.name))
		to = _requester_address(doc)
		if to:
			_send([to] if "@" in to else [_user_email(to)], subject, body, doc.name)

	if settings.enable_whatsapp_intake and doc.source == "WhatsApp" and doc.raised_by:
		from facilities_management.utils.whatsapp import send_whatsapp_message

		send_whatsapp_message(doc.raised_by, f"{subject}.")


# ---------------------------------------------------------------- email in/out

def on_communication_insert(doc, method=None):
	if doc.reference_doctype != TICKET or not doc.reference_name:
		return
	if doc.communication_type != "Communication":
		return
	if doc.sent_or_received == "Sent":
		return _on_staff_reply(doc)
	if doc.sent_or_received != "Received":
		return

	from facilities_management.utils.email_intake import _is_automated

	if _is_automated(doc):
		return
	settings = get_settings()
	received = frappe.db.count(
		"Communication",
		{"reference_doctype": TICKET, "reference_name": doc.reference_name, "sent_or_received": "Received"},
	)
	if received == 1:
		if settings.enable_email_intake:
			_enrich_from_founding_email(doc, settings)
		return
	_on_requester_reply(doc, settings)


def _enrich_from_founding_email(comm, settings):
	"""The email Frappe just used to create the ticket: identify who sent it."""
	ticket = frappe.get_doc(TICKET, comm.reference_name)
	sender = (comm.sender or "").strip()
	updates = {"source": "Email", "raised_by": sender}
	user = frappe.db.get_value("User", {"email": sender}, "name")
	if user:
		updates.update(requested_by=user, client_type="Internal")
	else:
		# clear the "user" default that the background worker's user would have left
		updates.update(requested_by=None, client_type="External", external_client_name=comm.sender_full_name or sender)
	if not ticket.description:
		updates["description"] = comm.content
	ticket.db_set(updates, notify=False)
	if settings.email_send_acknowledgement:
		send_acknowledgement(ticket)


def _on_staff_reply(comm):
	row = frappe.db.get_value(TICKET, comm.reference_name, ["status", "first_responded_on"], as_dict=True)
	if not row:
		return
	updates = {}
	if not row.first_responded_on:
		updates["first_responded_on"] = now_datetime()
	if row.status == "Open":
		updates["status"] = "In Progress"
	if updates:
		frappe.db.set_value(TICKET, comm.reference_name, updates)


def _on_requester_reply(comm, settings):
	row = frappe.db.get_value(TICKET, comm.reference_name, ["status", "assigned_to", "subject"], as_dict=True)
	if not row:
		return
	note = None
	if row.status in ("Resolved", "Closed") and flag_enabled(settings, "email_reopen_on_reply"):
		new_status = "In Progress" if row.assigned_to else "Open"
		frappe.db.set_value(TICKET, comm.reference_name, {
			"status": new_status, "resolved_on": None, "closed_on": None, "resolution_breach_notified": 0,
		})
		note = _("Reopened automatically: the requester replied by email while the ticket was {0}. "
				 "Status is now {1}.").format(row.status, new_status)
	elif row.status == "Waiting on Requester":
		frappe.db.set_value(TICKET, comm.reference_name, "status", "In Progress")
		note = _("Requester replied; status moved from Waiting on Requester to In Progress.")
	if note:
		frappe.get_doc({
			"doctype": "Comment", "comment_type": "Info", "reference_doctype": TICKET,
			"reference_name": comm.reference_name, "content": note,
		}).insert(ignore_permissions=True)

	if settings.enable_email_notifications and flag_enabled(settings, "email_notify_replies"):
		recipients = [_user_email(row.assigned_to)] if row.assigned_to else get_role_emails("Facilities Manager")
		snippet = (strip_html(comm.content or "") or "").strip()[:400]
		_send(
			recipients,
			_("Reply on Facilities Ticket {0}: {1}").format(comm.reference_name, row.subject),
			_("The requester replied to ticket {0}.<br><br>{1}").format(
				_link(comm.reference_name), frappe.utils.escape_html(snippet)),
			comm.reference_name,
		)


# ------------------------------------------------------ work order -> ticket

def sync_ticket_from_work_order(doc, method=None):
	"""Keep a linked ticket in step with the work order that was raised from it."""
	ticket_name = doc.get("linked_ticket")
	if not ticket_name or not doc.has_value_changed("status"):
		return
	if doc.status not in ("Completed", "Closed", "Rejected") or not frappe.db.exists(TICKET, ticket_name):
		return

	ticket = frappe.get_doc(TICKET, ticket_name)
	if ticket.status == "Closed":
		return
	if doc.status == "Rejected":
		ticket.add_comment("Info", _("Linked work order {0} was rejected. Review and decide the next step.").format(doc.name))
		return

	fallback = _("Resolved through work order {0}.").format(doc.name)
	if doc.status == "Completed" and ticket.status in OPEN_STATUSES:
		ticket.status = "Resolved"
		ticket.resolution_notes = ticket.resolution_notes or doc.resolution_notes or fallback
	elif doc.status == "Closed":
		if ticket.status in OPEN_STATUSES:
			ticket.status = "Resolved"
			ticket.resolution_notes = ticket.resolution_notes or doc.resolution_notes or fallback
			ticket.flags.ignore_permissions = True
			ticket.save()
		ticket.status = "Closed"
	else:
		return
	ticket.flags.ignore_permissions = True
	ticket.save()
	ticket.add_comment("Info", _("Status set to {0} because work order {1} is {2}.").format(
		_(ticket.status), doc.name, doc.status))


# ----------------------------------------------------------------- scheduler

def check_ticket_sla():
	"""Hourly: alert once for a missed first response and once for a missed resolution."""
	from facilities_management.utils.scheduler import _notify_role

	if not flag_enabled(get_settings(), "email_notify_sla_breach"):
		return
	now = now_datetime()
	tickets = frappe.get_all(
		TICKET,
		filters={"status": ["in", OPEN_STATUSES]},
		fields=["name", "subject", "priority", "status", "assigned_to", "first_responded_on",
				"response_due", "resolution_due", "response_breach_notified", "resolution_breach_notified"],
	)
	for t in tickets:
		if t.status == "Waiting on Requester":
			continue  # the clock is with the requester
		extra = [t.assigned_to] if t.assigned_to else None
		if not t.first_responded_on and t.response_due and t.response_due < now and not t.response_breach_notified:
			_notify_role(
				"Facilities Manager", _("First response overdue: ticket {0}").format(t.name),
				_("Facilities Ticket {0} ({1}, {2} priority) has had no response since {3}.").format(
					t.name, t.subject, t.priority, t.response_due),
				extra_users=extra, reference_doctype=TICKET, reference_name=t.name)
			frappe.db.set_value(TICKET, t.name, "response_breach_notified", 1, update_modified=False)
		if t.resolution_due and t.resolution_due < now and not t.resolution_breach_notified:
			_notify_role(
				"Facilities Manager", _("SLA breached: ticket {0}").format(t.name),
				_("Facilities Ticket {0} ({1}, {2} priority) passed its resolution due date of {3}.").format(
					t.name, t.subject, t.priority, t.resolution_due),
				extra_users=extra, reference_doctype=TICKET, reference_name=t.name)
			frappe.db.set_value(TICKET, t.name, "resolution_breach_notified", 1, update_modified=False)


def auto_close_resolved_tickets():
	"""Daily: close tickets that have sat in Resolved with no reply."""
	days = get_settings().get("ticket_auto_close_days") or 3
	stale = frappe.get_all(
		TICKET, filters={"status": "Resolved", "resolved_on": ["<=", add_days(now_datetime(), -days)]}, pluck="name"
	)
	for name in stale:
		frappe.db.set_value(TICKET, name, {"status": "Closed", "closed_on": now_datetime()})


# --------------------------------------------------------------------- setup

DEFAULT_CATEGORIES = (
	"Electrical", "Plumbing & Water", "HVAC / Air Conditioning", "Cleaning & Housekeeping",
	"Security & Access", "Furniture & Fittings", "IT & Network", "Grounds & Landscaping",
	"Vehicles & Transport", "Room / Space Request", "General Enquiry",
)


def ensure_ticket_categories():
	"""Idempotent: add the starter categories without touching ones already edited."""
	for name in DEFAULT_CATEGORIES:
		if not frappe.db.exists("Facilities Ticket Category", name):
			frappe.get_doc({"doctype": "Facilities Ticket Category", "category_name": name}).insert(
				ignore_permissions=True)
