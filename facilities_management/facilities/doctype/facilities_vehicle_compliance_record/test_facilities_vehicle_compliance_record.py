# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate


class TestFacilitiesVehicleComplianceRecord(IntegrationTestCase):
	def setUp(self):
		self.vehicle = frappe.get_doc({
			"doctype": "Facility Vehicle", "vehicle_name": "Test Lorry", "registration_number": "KZZ 111Z",
			"insurance_required": 1, "insurance_expiry": add_days(nowdate(), -5), "speed_governor_required": 1,
		}).insert(ignore_permissions=True)

	def record(self, **kw):
		doc = {"doctype": "Facilities Vehicle Compliance Record", "vehicle": self.vehicle.name, "compliance_type": "Insurance",
			"reference_number": "POL-1", "expiry_date": add_days(nowdate(), 365), "provider": "Test Insurer"}
		doc.update(kw)
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def test_expired_insurance_status(self):
		self.assertEqual(self.vehicle.insurance_status, "Overdue")
		self.assertEqual(self.vehicle.governor_status, "Unknown")

	def test_renewal_updates_vehicle(self):
		self.record()
		self.vehicle.reload()
		self.assertEqual(self.vehicle.insurance_policy_number, "POL-1")
		self.assertEqual(self.vehicle.insurance_status, "Valid")

	def test_older_record_does_not_override(self):
		self.record()
		self.record(reference_number="POL-OLD", expiry_date=add_days(nowdate(), 30))
		self.vehicle.reload()
		self.assertEqual(self.vehicle.insurance_policy_number, "POL-1")

	def test_speed_governor_record(self):
		self.record(compliance_type="Speed Governor", reference_number="SG-9", speed_limit_kph=80)
		self.vehicle.reload()
		self.assertEqual(self.vehicle.governor_certificate_number, "SG-9")
		self.assertEqual(self.vehicle.governor_status, "Valid")
