# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

FINANCE_ROLES = {"Accounts Manager", "System Manager"}


class FacilitiesPurchaseOrder(Document):
	def validate(self):
		self.calculate_total()
		self.stamp_review()
		self.check_payment_details()
		self.enforce_procedure_rules()

	def calculate_total(self):
		total = 0
		for row in self.items:
			row.amount = (row.qty or 0) * (row.rate or 0)
			total += row.amount
		self.total_amount = total
		self.grand_total = total + flt(self.vat_amount)

	def stamp_review(self):
		before = self.get_doc_before_save()
		if self.review_decision and (not before or before.review_decision != self.review_decision):
			self.reviewed_by = frappe.session.user
			self.reviewed_on = now_datetime()

	def check_payment_details(self):
		needs = {
			"Charge to ABS Account": [("charge_account", _("ABS Account to Charge"))],
			"M-Pesa Payment": [("mpesa_number", _("Paybill / Till Number")), ("mpesa_reference", _("Account / Reference Name"))],
			"Bank Transfer": [("bank_name", _("Bank Name")), ("bank_account_name", _("Account Name")), ("bank_account_number", _("Account Number"))],
		}.get(self.payment_option, [])
		missing = [label for field, label in needs if not self.get(field)]
		if missing:
			frappe.throw(_("{0} needs: {1}").format(_(self.payment_option), ", ".join(missing)))

	def moving_to(self, status):
		if self.status != status:
			return False
		before = self.get_doc_before_save()
		return not before or before.status != status

	def enforce_procedure_rules(self):
		if self.moving_to("Pending Approval"):
			missing = []
			if not self.items:
				missing.append(_("at least one item"))
			if not self.justification:
				missing.append(_("Justification / Purpose of Purchase"))
			if not self.quotation_attachment:
				missing.append(_("Approved Quotation"))
			if missing:
				frappe.throw(_("Before sending for approval add: {0}").format(", ".join(missing)))
		if self.moving_to("Approved"):
			if self.review_decision != "Approved":
				frappe.throw(_("Facilities / Procurement Review must be marked Approved first."))
			if not self.finance_approved_on:
				frappe.throw(_("Finance approval is required first. A Finance user must press Finance Approve."))
		if self.moving_to("Ordered") and not self.supplier_signatory:
			frappe.throw(_("Record the supplier's authorized signatory who acknowledged this purchase order."))
		if self.moving_to("Received"):
			missing = []
			if not (self.received_by and self.received_on and self.receipt_condition):
				missing.append(_("Received By, Date Received and Condition"))
			if not self.delivery_note:
				missing.append(_("Delivery Note"))
			if missing:
				frappe.throw(_("Before marking Received add: {0}").format(", ".join(missing)))


@frappe.whitelist()
def finance_approve(purchase_order):
	"""Finance confirms that funds are available and approves the purchase."""
	if not (FINANCE_ROLES & set(frappe.get_roles())):
		frappe.throw(_("Only Finance (Accounts Manager) can give Finance approval."), frappe.PermissionError)
	doc = frappe.get_doc("Facilities Purchase Order", purchase_order)
	if doc.status not in ("Pending Approval", "Approved"):
		frappe.throw(_("Finance approval is given while the purchase order is Pending Approval."))
	doc.db_set({"finance_approved_by": frappe.session.user, "finance_approved_on": now_datetime()})
	doc.add_comment("Info", _("Finance approval given by {0}.").format(frappe.session.user_fullname))
	return doc.finance_approved_on
