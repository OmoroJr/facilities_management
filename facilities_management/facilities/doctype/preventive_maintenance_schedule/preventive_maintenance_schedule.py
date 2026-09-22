# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PreventiveMaintenanceSchedule(Document):
	def validate(self):
		if not self.next_due_date:
			self.next_due_date = self.start_date

	def compute_next_due_date(self):
		"""Advance next_due_date by one interval based on frequency."""
		from frappe.utils import add_days, getdate

		interval_map = {
			"Daily": 1,
			"Weekly": 7,
			"Monthly": 30,
			"Quarterly": 91,
			"Semi-Annual": 182,
			"Annual": 365,
		}
		days = self.custom_interval_days if self.frequency == "Custom" else interval_map.get(self.frequency, 30)
		base = getdate(self.next_due_date) if self.next_due_date else getdate()
		self.next_due_date = add_days(base, days)
		self.save(ignore_permissions=True)

	def generate_work_order(self):
		"""Create a Preventive Maintenance Facilities Work Order for this schedule."""
		wo = frappe.new_doc("Facilities Work Order")
		wo.subject = f"Preventive Maintenance: {self.facility_asset}"
		wo.work_order_type = "Preventive Maintenance"
		wo.facility_asset = self.facility_asset
		wo.priority = "Medium"
		wo.description = "Auto-generated from Preventive Maintenance Schedule: " + self.name
		if self.assigned_technician:
			wo.assigned_to = self.assigned_technician
		wo.insert(ignore_permissions=True)
		self.last_generated_work_order = wo.name
		self.compute_next_due_date()
		return wo.name
