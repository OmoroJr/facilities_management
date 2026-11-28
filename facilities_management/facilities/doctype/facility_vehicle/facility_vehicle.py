# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from facilities_management.utils.ntsa import compute_all_statuses


class FacilityVehicle(Document):
	def validate(self):
		if self.last_ntsa_inspection and self.ntsa_inspection_due and self.ntsa_inspection_due <= self.last_ntsa_inspection:
			frappe.throw(_("The inspection due date must be after the last NTSA inspection."))
		for field, value in compute_all_statuses(self).items():
			self.set(field, value)
