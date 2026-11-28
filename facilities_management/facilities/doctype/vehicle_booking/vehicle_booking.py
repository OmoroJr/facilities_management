# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate


class VehicleBooking(Document):
	def validate(self):
		self.check_overlap()
		self.check_compliance()

	def check_overlap(self):
		if not (self.vehicle and self.from_datetime and self.to_datetime):
			return
		if self.to_datetime <= self.from_datetime:
			frappe.throw(_("'To' must be after 'From'"))

		overlapping = frappe.db.sql('''
			select name from `tabVehicle Booking`
			where vehicle = %(vehicle)s
				and name != %(name)s
				and status in ('Requested', 'Confirmed')
				and from_datetime < %(to)s
				and to_datetime > %(from)s
		''', {
			"vehicle": self.vehicle,
			"name": self.name or "New Vehicle Booking",
			"from": self.from_datetime,
			"to": self.to_datetime,
		})
		if overlapping:
			frappe.throw(_("Vehicle {0} is already booked for part of this time slot ({1})").format(
				self.vehicle, overlapping[0][0]))

	def check_compliance(self):
		"""Warn (or block, if Facilities Settings says so) when the vehicle's NTSA inspection, insurance or speed governor has expired."""
		if self.status not in ("Requested", "Confirmed") or not (self.vehicle and self.from_datetime):
			return
		from facilities_management.utils.ntsa import COMPLIANCE_ITEMS

		fields = ["registration_number"] + [f for item in COMPLIANCE_ITEMS for f in item[1:3]]
		v = frappe.db.get_value("Facility Vehicle", self.vehicle, fields, as_dict=True)
		if not v:
			return
		expired = []
		for label, required, expiry, _status in COMPLIANCE_ITEMS:
			if cint(v.get(required)) and v.get(expiry) and getdate(v.get(expiry)) < getdate(self.from_datetime):
				expired.append(_("{0} expired on {1}").format(_(label), frappe.utils.formatdate(v.get(expiry))))
		if not expired:
			return
		msg = _("{0}: {1}.").format(v.registration_number, "; ".join(expired))
		if cint(frappe.get_cached_doc("Facilities Settings").get("block_expired_ntsa_bookings")):
			frappe.throw(msg)
		frappe.msgprint(msg, indicator="orange", alert=True)
