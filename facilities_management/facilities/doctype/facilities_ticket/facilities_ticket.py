# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

OPEN_STATUSES = ("Open", "In Progress", "Waiting on Requester")
DONE_STATUSES = ("Resolved", "Closed")
STAFF_ROLES = {"System Manager", "Facilities Manager", "Facilities Technician"}

# Fields a requester (Facilities Client) must not be able to change themselves.
STAFF_ONLY_FIELDS = (
	"status", "priority", "category", "assigned_to", "linked_work_order",
	"resolution_notes", "response_due", "resolution_due",
)

# Ticket category -> the trade on the ABS work order form.
TRADES = {
	"Electrical": "Electrical", "Plumbing & Water": "Plumbing", "Carpentry": "Carpentry",
	"Masonry": "Masonry", "Painting": "Painting",
}

# Hours, by priority. A category can override either value.
RESPONSE_HOURS = {"Critical": 1, "High": 4, "Medium": 8, "Low": 24}
RESOLUTION_HOURS = {"Critical": 4, "High": 24, "Medium": 72, "Low": 168}


class FacilitiesTicket(Document):
	def validate(self):
		self.guard_requester_edits()
		self.fill_requester()
		self.apply_category_defaults()
		self.set_sla()
		self.check_status_requirements()
		self.stamp_status_changes()

	# -- validation helpers -------------------------------------------------

	def is_requester_only(self):
		roles = set(frappe.get_roles())
		return "Facilities Client" in roles and not (roles & STAFF_ROLES)

	def guard_requester_edits(self):
		"""Requesters can describe a problem but not triage, assign or close it."""
		if not self.is_requester_only():
			return
		if self.is_new():
			self.status = "Open"
			self.assigned_to = None
			return
		before = self.get_doc_before_save()
		for field in STAFF_ONLY_FIELDS:
			if before and self.get(field) != before.get(field):
				frappe.throw(_("Only Facilities staff can change {0}.").format(_(self.meta.get_label(field))))

	def fill_requester(self):
		if self.requested_by and not self.raised_by:
			self.raised_by = frappe.db.get_value("User", self.requested_by, "email")

	def get_category(self):
		if not self.category:
			return None
		return frappe.db.get_value(
			"Facilities Ticket Category", self.category,
			["default_assignee", "default_priority", "response_hours", "resolution_hours"], as_dict=True,
		)

	def apply_category_defaults(self):
		cat = self.get_category()
		if self.is_new() and cat:
			if not self.assigned_to and cat.default_assignee:
				self.assigned_to = cat.default_assignee
			if not self.priority and cat.default_priority:
				self.priority = cat.default_priority
		if not self.priority:
			self.priority = "Medium"

	def set_sla(self):
		if not (self.is_new() or not self.resolution_due or self.has_value_changed("priority")
				or self.has_value_changed("category")):
			return
		cat = self.get_category()
		anchor = now_datetime() if self.is_new() else get_datetime(self.creation)
		response = (cat and cat.response_hours) or RESPONSE_HOURS.get(self.priority, 8)
		resolution = (cat and cat.resolution_hours) or RESOLUTION_HOURS.get(self.priority, 72)
		self.response_due = add_to_date(anchor, hours=response)
		self.resolution_due = add_to_date(anchor, hours=resolution)

	def check_status_requirements(self):
		if self.status == "Resolved" and not (self.resolution_notes or "").strip():
			frappe.throw(_("Enter resolution notes before resolving the ticket."))

	def stamp_status_changes(self):
		if self.is_new() or not self.has_value_changed("status"):
			return
		now, status = now_datetime(), self.status
		if status != "Open" and not self.first_responded_on:
			self.first_responded_on = now
		if status == "Resolved":
			self.resolved_on = now
			self.closed_on = None
		elif status == "Closed":
			self.closed_on = now
			self.resolved_on = self.resolved_on or now
		elif status in OPEN_STATUSES:
			# reopened
			self.resolved_on = None
			self.closed_on = None
			self.resolution_breach_notified = 0

	# -- events -------------------------------------------------------------

	def after_insert(self):
		from facilities_management.utils.ticketing import notify_ticket_created

		notify_ticket_created(self)

	def on_update(self):
		from facilities_management.utils.ticketing import notify_ticket_update

		notify_ticket_update(self)


@frappe.whitelist()
def make_work_order(ticket):
	"""Raise a Facilities Work Order for a ticket that needs a technician on site."""
	doc = frappe.get_doc("Facilities Ticket", ticket)
	doc.check_permission("write")

	if doc.linked_work_order:
		frappe.throw(_("{0} already has work order {1}.").format(doc.name, doc.linked_work_order))
	if doc.status in DONE_STATUSES:
		frappe.throw(_("Reopen the ticket before raising a work order."))

	trade = TRADES.get(doc.category)
	wo = frappe.get_doc({
		"doctype": "Facilities Work Order",
		"trade_category": trade or ("Other" if doc.category else None),
		"trade_other": None if trade else doc.category,
		"subject": doc.subject,
		"work_order_type": "Corrective",
		"status": "Submitted",
		"priority": doc.priority,
		"requested_by": doc.requested_by,
		"raised_by": doc.raised_by,
		"department": doc.department,
		"client_type": doc.client_type,
		"external_client_name": doc.external_client_name,
		"facility_asset": doc.facility_asset,
		"room": doc.room,
		"location_detail": doc.location_detail,
		"source": doc.source,
		"description": doc.description,
		"attachment": doc.attachment,
		"linked_ticket": doc.name,
	})
	wo.flags.ignore_permissions = True  # triage staff may not hold Create on Work Order
	wo.insert()
	if not doc.requested_by:
		# external requester: undo the field-level "user" default
		wo.db_set("requested_by", None, update_modified=False)

	doc.linked_work_order = wo.name
	if doc.status == "Open":
		doc.status = "In Progress"
	if not doc.assigned_to:
		doc.assigned_to = frappe.session.user
	doc.save()
	doc.add_comment("Info", _("Work order {0} raised from this ticket.").format(wo.name))
	return wo.name
