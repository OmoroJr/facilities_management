# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FacilitiesWorkOrder(Document):
	def validate(self):
		self.set_sla_due_date()
		self.auto_submit_external_intake()

	def auto_submit_external_intake(self):
		# Tickets created by inbound email/WhatsApp have no human present to
		# press "Submit" - move them straight into the approval queue.
		if self.is_new() and self.status == "Draft" and self.source in ("Email", "WhatsApp"):
			self.status = "Submitted"

	def set_sla_due_date(self):
		from frappe.utils import now_datetime, add_to_date

		hours_map = {"Critical": 4, "High": 24, "Medium": 72, "Low": 168}
		if not self.sla_due_date and self.priority:
			self.sla_due_date = add_to_date(now_datetime(), hours=hours_map.get(self.priority, 72))

	def on_update(self):
		self.handle_status_side_effects()
		self.send_status_notification()

	def handle_status_side_effects(self):
		from frappe.utils import now_datetime

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
