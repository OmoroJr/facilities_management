# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleBooking(Document):
	def validate(self):
		self.check_overlap()

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
