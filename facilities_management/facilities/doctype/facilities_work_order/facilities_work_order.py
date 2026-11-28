# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, flt, now_datetime

STAFF_ROLES = {"System Manager", "Facilities Manager", "Facilities Technician"}
COST_NEEDS_ALLOCATION = ("Department-Specific Cost", "Shared / Exceptional Area")


class FacilitiesWorkOrder(Document):
	def validate(self):
		self.set_sla_due_date()
		self.auto_submit_external_intake()
		self.apply_policy_item()
		self.calculate_estimates()
		self.stamp_review_and_acknowledgement()
		self.enforce_procedure_rules()

	def auto_submit_external_intake(self):
		# Tickets created by inbound email/WhatsApp have no human present to
		# press "Submit" - move them straight into the approval queue.
		if self.is_new() and self.status == "Draft" and self.source in ("Email", "WhatsApp"):
			self.status = "Submitted"

	def set_sla_due_date(self):
		from frappe.utils import add_to_date

		hours_map = {"Critical": 4, "High": 24, "Medium": 72, "Low": 168}
		if not self.sla_due_date and self.priority:
			self.sla_due_date = add_to_date(now_datetime(), hours=hours_map.get(self.priority, 72))

	# -- ABS Work Order Procedure Manual ------------------------------------

	def apply_policy_item(self):
		"""Step 2.7: classify the cost from the Cost Management Policy item."""
		if self.policy_item and not self.cost_category:
			self.cost_category = frappe.db.get_value("Facilities Cost Policy Item", self.policy_item, "cost_category")

	def calculate_estimates(self):
		"""Form G/H: quotation total and duration."""
		self.estimated_total = sum(flt(self.get(f)) for f in ("est_materials", "est_labour", "est_transport", "est_other"))
		if self.proposed_start_date and self.proposed_end_date:
			if self.proposed_end_date < self.proposed_start_date:
				frappe.throw(_("Proposed End Date cannot be before Proposed Start Date."))
			self.estimated_days = date_diff(self.proposed_end_date, self.proposed_start_date) + 1

	def stamp_review_and_acknowledgement(self):
		before = self.get_doc_before_save()
		if self.facilities_decision and (not before or before.facilities_decision != self.facilities_decision):
			self.reviewed_by = frappe.session.user
			self.reviewed_on = now_datetime()
		if not self.acknowledged_on and (self.facilities_decision or self.status not in ("Draft", "Submitted")):
			self.acknowledged_on = now_datetime()

	def is_emergency(self):
		return self.cost_category == "Emergency" or self.priority == "Critical"

	def moving_to(self, status):
		if self.status != status:
			return False
		before = self.get_doc_before_save()
		return not before or before.status != status

	def enforce_procedure_rules(self):
		settings = frappe.get_cached_doc("Facilities Settings")

		if self.moving_to("Pending Approval"):
			self.require_form_fields()
		if self.moving_to("Approved") and not self.is_emergency():
			self.require_cost_allocation()
		if self.moving_to("In Progress") and cint(self.requires_contract):
			self.require_signed_contract()
		if cint(settings.require_completion_confirmation):
			if self.moving_to("Closed"):
				self.require_completion_evidence()
			self.check_final_payment()

	def require_form_fields(self):
		"""The mandatory fields of the Maintenance Work Order Form."""
		needed = [("department", _("Requesting Department")), ("description", _("Description"))]
		if not self.is_emergency():
			needed += [("contact_person_name", _("On-site Contact Name")), ("contact_person_phone", _("On-site Contact Phone"))]
		missing = [label for field, label in needed if not self.get(field)]
		if missing:
			frappe.throw(_("Complete these fields before sending for approval: {0}").format(", ".join(missing)))

	def require_cost_allocation(self):
		"""Step 2.7: cost must be classified, and charged and approved in writing where it is not a general cost."""
		if not self.cost_category:
			frappe.throw(_("Choose the Cost Category (or a Policy Item) before this work order is approved."))
		if self.cost_category not in COST_NEEDS_ALLOCATION:
			return
		missing = []
		if not self.cost_center:
			missing.append(_("Charge Account / Cost Center"))
		if not self.approval_method:
			missing.append(_("How Approval Was Given"))
		elif self.approval_method in ("Email", "Signed Form") and not self.approval_evidence:
			missing.append(_("Approval Evidence"))
		if not cint(self.cost_sharing_agreed):
			missing.append(_("Cost Sharing Agreed With Facilities"))
		if missing:
			frappe.throw(_("{0} needs the following before approval: {1}").format(_(self.cost_category), ", ".join(missing)))

	def require_signed_contract(self):
		"""Step 6: the technician or vendor must sign a contract before work starts."""
		if not self.linked_contract:
			frappe.throw(_("Link the signed contract before starting this work order."))
		contract = frappe.db.get_value("Facilities Maintenance Contract", self.linked_contract, ["signed_on", "status"], as_dict=True)
		if not contract or not contract.signed_on:
			frappe.throw(_("Contract {0} has no signing date. It must be signed before work starts.").format(self.linked_contract))
		if contract.status != "Active":
			frappe.throw(_("Contract {0} is {1}, not Active.").format(self.linked_contract, contract.status))

	def require_completion_evidence(self):
		"""Steps 8 and 9: written client confirmation and a Facilities inspection before closing."""
		missing = []
		if not (self.client_confirmed_by and self.client_confirmed_on and self.confirmation_method):
			missing.append(_("Written completion confirmation from the client"))
		if not (self.inspected_by and self.inspection_date):
			missing.append(_("Facilities inspection (who and when)"))
		if missing:
			frappe.throw(_("Before closing: {0}").format("; ".join(missing)))

	def check_final_payment(self):
		before = self.get_doc_before_save()
		if not cint(self.final_payment_approved) or (before and cint(before.final_payment_approved)):
			return
		if not (self.inspected_by and self.inspection_date):
			frappe.throw(_("Record the Facilities inspection before approving final payment."))
		if not (self.client_confirmed_on or cint(self.warranty_provided)):
			frappe.throw(_("Written client confirmation is required before final payment, unless a warranty is provided."))

	# -- status side effects ------------------------------------------------

	def on_update(self):
		self.handle_status_side_effects()
		self.send_status_notification()

	def handle_status_side_effects(self):
		if self.has_value_changed("status"):
			if self.status == "Approved":
				self.db_set("approval_date", now_datetime())
			elif self.status == "In Progress" and not self.started_on:
				self.db_set("started_on", now_datetime())
			elif self.status == "Completed":
				self.db_set("completed_on", now_datetime())
			elif self.status == "Closed":
				self.db_set("closed_on", now_datetime())

	def send_status_notification(self):
		if not self.has_value_changed("status"):
			return
		from facilities_management.utils.notifications import notify_work_order_status_change

		notify_work_order_status_change(self)


@frappe.whitelist()
def acknowledge(work_order):
	"""Step 4: Facilities confirms receipt of a work order (target: within 24 hours)."""
	if not (STAFF_ROLES & set(frappe.get_roles())):
		frappe.throw(_("Only Facilities staff can acknowledge a work order."), frappe.PermissionError)
	doc = frappe.get_doc("Facilities Work Order", work_order)
	if doc.acknowledged_on:
		return doc.acknowledged_on
	now = now_datetime()
	doc.db_set("acknowledged_on", now)
	doc.add_comment("Info", _("Receipt acknowledged by {0}.").format(frappe.session.user_fullname))

	settings = frappe.get_cached_doc("Facilities Settings")
	to = doc.raised_by if doc.raised_by and "@" in doc.raised_by else frappe.db.get_value("User", doc.requested_by, "email")
	if to and settings.enable_email_notifications:
		frappe.sendmail(
			recipients=[to],
			subject=_("Work order {0} received").format(doc.name),
			message=_("Facilities has received your work order <b>{0}</b> ({1}) and will update you as it progresses.").format(doc.name, doc.subject),
			reference_doctype=doc.doctype, reference_name=doc.name,
		)
	return now
