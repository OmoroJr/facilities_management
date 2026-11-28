# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FacilitiesMaintenanceContract(Document):
	def validate(self):
		value = flt(self.contract_value)
		self.deposit_amount = value * flt(self.deposit_percent) / 100
		self.balance_payable = value - self.deposit_amount
		if flt(self.deposit_percent) > 100:
			frappe.throw(_("Deposit % cannot be more than 100."))
		if self.start_date and self.end_date and self.end_date < self.start_date:
			frappe.throw(_("End Date cannot be before Start Date."))
