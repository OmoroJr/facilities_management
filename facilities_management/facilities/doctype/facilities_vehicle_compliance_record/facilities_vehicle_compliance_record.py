# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from facilities_management.utils.ntsa import refresh_vehicle_status


class FacilitiesVehicleComplianceRecord(Document):
	def validate(self):
		if self.start_date and self.expiry_date and getdate(self.expiry_date) <= getdate(self.start_date):
			frappe.throw(_("The expiry date must be after the start date."))

	def on_update(self):
		self.apply_to_vehicle()

	def apply_to_vehicle(self):
		"""Make this record the vehicle's current cover / certificate when it runs later than the one on file."""
		if self.compliance_type == "Insurance":
			expiry_field, extra = "insurance_expiry", {"insurance_provider": self.provider, "insurance_policy_number": self.reference_number}
		else:
			expiry_field = "governor_expiry"
			extra = {"governor_certificate_number": self.reference_number}
			if self.speed_limit_kph:
				extra["governor_speed_limit"] = self.speed_limit_kph
		current = frappe.db.get_value("Facility Vehicle", self.vehicle, expiry_field)
		if current and getdate(current) > getdate(self.expiry_date):
			frappe.msgprint(
				_("{0} already runs to {1}, which is later than this record, so the vehicle was not changed.").format(
					_(self.compliance_type), frappe.utils.formatdate(current)),
				indicator="orange", alert=True)
			return
		frappe.db.set_value("Facility Vehicle", self.vehicle, {expiry_field: self.expiry_date, **extra})
		refresh_vehicle_status(self.vehicle)
		if not self.applied_to_vehicle:
			self.db_set("applied_to_vehicle", 1, update_modified=False)
