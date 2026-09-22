# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FacilitiesPurchaseOrder(Document):
	def validate(self):
		self.calculate_total()

	def calculate_total(self):
		total = 0
		for row in self.items:
			row.amount = (row.qty or 0) * (row.rate or 0)
			total += row.amount
		self.total_amount = total
