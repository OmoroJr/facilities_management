# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SafetyInspection(Document):
	def on_update(self):
		if self.corrective_action_required and not self.linked_work_order:
			self.create_corrective_work_order()

	def create_corrective_work_order(self):
		wo = frappe.new_doc("Facilities Work Order")
		wo.subject = f"Corrective action: {self.inspection_type} inspection"
		wo.work_order_type = "Corrective"
		wo.facility_asset = self.facility_asset
		wo.priority = "High" if self.status == "Failed" else "Medium"
		wo.description = self.findings or ""
		wo.insert(ignore_permissions=True)
		self.db_set("linked_work_order", wo.name)
