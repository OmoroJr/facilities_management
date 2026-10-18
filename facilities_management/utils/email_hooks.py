# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""Document-event email hooks for Facilities Work Orders.

Wired up in hooks.py `doc_events`:
  Facilities Work Order.after_insert  -> on_work_order_created
  Facilities Work Order.on_update     -> on_work_order_assignment_change
  Communication.after_insert          -> notify_on_ticket_reply
  Comment.after_insert                -> notify_on_ticket_comment
"""

import frappe
from frappe import _
from frappe.utils import get_url_to_form

from facilities_management.utils.notifications import (
	flag_enabled,
	get_role_emails,
	get_settings,
)

WO = "Facilities Work Order"


def _send(recipients, subject, message, doc_name):
	recipients = sorted({r for r in recipients if r})
	if not recipients:
		return
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype=WO,
			reference_name=doc_name,
		)
	except Exception:
		frappe.log_error(title="Facilities: email hook failed")


def _user_email(user):
	return frappe.db.get_value("User", user, "email") if user else None


def _link(name):
	url = get_url_to_form(WO, name)
	return f'<a href="{url}">{name}</a>'


def on_work_order_created(doc, method=None):
	"""Alert Facilities Managers (and the default approver) about a new ticket."""
	settings = get_settings()
	if not settings.enable_email_notifications or not flag_enabled(settings, "email_notify_new_ticket"):
		return

	recipients = set(get_role_emails("Facilities Manager"))
	recipients.add(_user_email(settings.default_approver))
	# don't alert people about tickets they raised themselves
	recipients.discard(_user_email(doc.requested_by))

	message = _(
		"A new work order has been logged.<br><br>"
		"Ticket: {0}<br>Subject: {1}<br>Priority: {2}<br>Type: {3}<br>Raised by: {4}"
	).format(
		_link(doc.name),
		doc.subject,
		doc.priority,
		doc.work_order_type,
		doc.external_client_name or doc.requested_by or doc.raised_by or "-",
	)
	_send(recipients, _("New Facilities Work Order {0}: {1}").format(doc.name, doc.subject), message, doc.name)


def on_work_order_assignment_change(doc, method=None):
	"""Email the technician when the assignee changes outside a status change
	(status-driven 'Assigned' mail is handled in notifications.py)."""
	if doc.is_new() or not doc.has_value_changed("assigned_to") or not doc.assigned_to:
		return
	if doc.has_value_changed("status"):
		return  # notify_work_order_status_change already covers it
	settings = get_settings()
	if not settings.enable_email_notifications:
		return
	message = _("Work Order {0} ({1}) has been assigned to you.<br>Priority: {2}<br>SLA due: {3}").format(
		_link(doc.name), doc.subject, doc.priority, doc.sla_due_date or "-"
	)
	_send(
		[_user_email(doc.assigned_to)],
		_("Facilities Work Order {0} has been assigned to you").format(doc.name),
		message,
		doc.name,
	)


def _reopen_if_closed(wo_name, doc):
	"""A customer replied on a Completed/Closed ticket: put it back in play.

	Goes to Assigned when a technician is on it, otherwise Approved (so the
	hourly escalation picks it up). Status is set with db_set, bypassing the
	workflow, because there is no human present to press a button.
	"""
	wo = frappe.db.get_value(WO, wo_name, ["status", "assigned_to"], as_dict=True)
	if not wo or wo.status not in ("Completed", "Closed"):
		return None
	new_status = "Assigned" if wo.assigned_to else "Approved"
	frappe.db.set_value(
		WO,
		wo_name,
		{
			"status": new_status,
			"completed_on": None,
			"closed_on": None,
			"sla_breach_notified": 0,
		},
	)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": WO,
			"reference_name": wo_name,
			"content": _("Reopened automatically: customer replied by email while the ticket was {0}. Status is now {1}.").format(
				wo.status, new_status
			),
		}
	).insert(ignore_permissions=True)
	return wo.status


def notify_on_ticket_reply(doc, method=None):
	"""A requester replied by email to an existing ticket: reopen it if it was
	finished, and tell the assignee (or the managers if nobody has it)."""
	from facilities_management.utils.email_intake import _is_automated

	if doc.reference_doctype != WO or not doc.reference_name:
		return
	if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
		return
	if _is_automated(doc):
		return

	received = frappe.db.count(
		"Communication",
		{"reference_doctype": WO, "reference_name": doc.reference_name, "sent_or_received": "Received"},
	)
	if received <= 1:
		return  # founding email - on_work_order_created / acknowledgement cover it

	settings = get_settings()
	reopened_from = None
	if flag_enabled(settings, "email_reopen_on_reply"):
		reopened_from = _reopen_if_closed(doc.reference_name, doc)

	if not settings.enable_email_notifications or not flag_enabled(settings, "email_notify_replies"):
		return

	wo = frappe.db.get_value(
		WO, doc.reference_name, ["subject", "assigned_to", "status"], as_dict=True
	)
	if not wo:
		return
	recipients = [_user_email(wo.assigned_to)] if wo.assigned_to else get_role_emails("Facilities Manager")
	message = _("{0} replied on ticket {1} ({2}, status: {3}):<br><br>{4}").format(
		doc.sender_full_name or doc.sender, _link(doc.reference_name), wo.subject, wo.status, doc.content or ""
	)
	subject = _("New reply on Facilities Work Order {0}").format(doc.reference_name)
	if reopened_from:
		message = _("<b>This ticket was {0} and has been reopened.</b><br><br>").format(reopened_from) + message
		subject = _("Reopened: Facilities Work Order {0}").format(doc.reference_name)
	_send(recipients, subject, message, doc.reference_name)


def notify_on_ticket_comment(doc, method=None):
	"""Internal comment on a ticket - tell the assignee (never the requester)."""
	if doc.reference_doctype != WO or doc.comment_type != "Comment" or not doc.reference_name:
		return
	settings = get_settings()
	if not settings.enable_email_notifications or not flag_enabled(settings, "email_notify_replies"):
		return
	assigned_to = frappe.db.get_value(WO, doc.reference_name, "assigned_to")
	if not assigned_to or assigned_to == doc.owner:
		return
	message = _("{0} commented on {1}:<br><br>{2}").format(
		frappe.utils.get_fullname(doc.owner), _link(doc.reference_name), doc.content or ""
	)
	_send(
		[_user_email(assigned_to)],
		_("New comment on Facilities Work Order {0}").format(doc.reference_name),
		message,
		doc.reference_name,
	)
