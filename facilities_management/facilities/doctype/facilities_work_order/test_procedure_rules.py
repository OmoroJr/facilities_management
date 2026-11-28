# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestProcedureRules(IntegrationTestCase):
	def make(self, **kw):
		doc = {"doctype": "Facilities Work Order", "subject": "Leaking tap", "department": None, "description": "Tap leaks",
			"priority": "Medium", "raised_by": "req@example.com", "source": "Email"}
		doc.update(kw)
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def test_quotation_total(self):
		wo = self.make(est_materials=1000, est_labour=500, est_transport=100, est_other=50)
		self.assertEqual(wo.estimated_total, 1650)

	def test_cannot_approve_without_cost_category(self):
		wo = self.make()
		wo.status = "Approved"
		self.assertRaises(frappe.ValidationError, wo.save)

	def test_department_cost_needs_charge_account(self):
		wo = self.make(cost_category="Department-Specific Cost")
		wo.status = "Approved"
		self.assertRaises(frappe.ValidationError, wo.save)

	def test_cannot_close_without_confirmation(self):
		wo = self.make(cost_category="General Facilities Cost")
		wo.db_set("status", "Completed")
		wo.reload()
		wo.status = "Closed"
		self.assertRaises(frappe.ValidationError, wo.save)
