# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate


class TestFacilitiesNTSABooking(IntegrationTestCase):
	def setUp(self):
		self.vehicle = frappe.get_doc({
			"doctype": "Facility Vehicle", "vehicle_name": "Test Van", "registration_number": "KZZ 999Z",
			"ntsa_inspection_required": 1, "ntsa_inspection_due": add_days(nowdate(), 10),
		}).insert(ignore_permissions=True)

	def booking(self, **kw):
		doc = {"doctype": "Facilities NTSA Booking", "vehicle": self.vehicle.name}
		doc.update(kw)
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def test_vehicle_status_due_soon(self):
		self.assertEqual(self.vehicle.ntsa_status, "Due Soon")

	def test_booked_needs_appointment_date(self):
		b = self.booking()
		b.status = "Booked"
		self.assertRaises(frappe.ValidationError, b.save)

	def test_pass_resets_vehicle_due_date(self):
		b = self.booking()
		b.update({"status": "Passed", "result_date": nowdate(), "certificate_number": "C-1", "certificate_expiry": add_days(nowdate(), 365)})
		b.save()
		self.vehicle.reload()
		self.assertEqual(str(self.vehicle.ntsa_inspection_due), str(add_days(nowdate(), 365)))
		self.assertEqual(self.vehicle.ntsa_status, "Valid")

	def test_failure_needs_reasons(self):
		b = self.booking()
		b.update({"status": "Failed", "result_date": nowdate()})
		self.assertRaises(frappe.ValidationError, b.save)
