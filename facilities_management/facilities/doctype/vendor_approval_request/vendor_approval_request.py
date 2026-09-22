# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VendorApprovalRequest(Document):
	def on_update(self):
		if self.has_value_changed("status") and self.status == "Approved" and not self.proposed_vendor:
			self.create_supplier()

	def create_supplier(self):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = self.vendor_name
		supplier.supplier_group = "All Supplier Groups"
		supplier.insert(ignore_permissions=True)
		self.db_set("proposed_vendor", supplier.name)
