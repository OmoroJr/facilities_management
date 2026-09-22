# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FacilityAsset(Document):
	def autoname(self):
		if not self.asset_code:
			prefix = "".join([w[0] for w in (self.asset_category or "FA").split()]).upper()[:3] or "FA"
			self.asset_code = frappe.model.naming.make_autoname(prefix + "-.#####")
		self.name = self.asset_code
