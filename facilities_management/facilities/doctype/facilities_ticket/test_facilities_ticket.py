# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestFacilitiesTicket(IntegrationTestCase):
	def make(self, **kw):
		return frappe.get_doc(
			{"doctype": "Facilities Ticket", "subject": "Leaking tap in Block A", "raised_by": "req@example.com", **kw}
		).insert(ignore_permissions=True)

	def test_defaults_and_sla(self):
		t = self.make(priority="High")
		self.assertEqual(t.status, "Open")
		self.assertTrue(t.response_due and t.resolution_due)
		self.assertLess(t.response_due, t.resolution_due)

	def test_resolve_requires_notes(self):
		t = self.make()
		t.status = "Resolved"
		self.assertRaises(frappe.ValidationError, t.save)
		t.resolution_notes = "Washer replaced"
		t.save()
		self.assertTrue(t.resolved_on)
		self.assertTrue(t.first_responded_on)

	def test_reopen_clears_resolution_dates(self):
		t = self.make()
		t.status, t.resolution_notes = "Resolved", "Done"
		t.save()
		t.status = "Open"
		t.save()
		self.assertFalse(t.resolved_on)
