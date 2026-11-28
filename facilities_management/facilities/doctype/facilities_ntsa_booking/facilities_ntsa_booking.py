# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from facilities_management.utils.ntsa import compute_status, get_soon_days, notify, refresh_vehicle_status


class FacilitiesNTSABooking(Document):
	def validate(self):
		self.fetch_due_date()
		self.check_required_for_status()
		self.check_dates()

	def fetch_due_date(self):
		if self.vehicle:
			self.due_date = frappe.db.get_value("Facility Vehicle", self.vehicle, "ntsa_inspection_due")

	def moving_to(self, status):
		if self.status != status:
			return False
		before = self.get_doc_before_save()
		return not before or before.status != status

	def check_required_for_status(self):
		if self.moving_to("Booked") and not self.appointment_date:
			frappe.throw(_("Enter the Appointment Date before marking the booking as Booked."))
		if self.moving_to("Passed"):
			missing = [label for f, label in (("result_date", _("Inspection Date")), ("certificate_number", _("Certificate Number")),
											  ("certificate_expiry", _("Certificate Expiry"))) if not self.get(f)]
			if missing:
				frappe.throw(_("To record a pass, enter: {0}").format(", ".join(missing)))
		if self.moving_to("Failed"):
			missing = [label for f, label in (("result_date", _("Inspection Date")), ("failure_reasons", _("Reasons for Failure"))) if not self.get(f)]
			if missing:
				frappe.throw(_("To record a failure, enter: {0}").format(", ".join(missing)))

	def check_dates(self):
		if self.result_date and self.certificate_expiry and getdate(self.certificate_expiry) <= getdate(self.result_date):
			frappe.throw(_("Certificate Expiry must be after the Inspection Date."))
		if self.result_date and getdate(self.result_date) > getdate(nowdate()):
			frappe.throw(_("The Inspection Date cannot be in the future."))

	def on_update(self):
		if self.has_value_changed("status"):
			if self.status == "Passed":
				self.apply_pass_to_vehicle()
			elif self.status == "Booked":
				self.send_booking_confirmation()
			elif self.status == "Failed":
				self.notify_failure()

	def apply_pass_to_vehicle(self):
		"""A pass resets the vehicle's inspection clock."""
		frappe.db.set_value("Facility Vehicle", self.vehicle, {
			"last_ntsa_inspection": self.result_date,
			"ntsa_inspection_due": self.certificate_expiry,
			"ntsa_certificate_number": self.certificate_number,
		})
		refresh_vehicle_status(self.vehicle)
		# any other open booking for the same vehicle is now moot
		for name in frappe.get_all("Facilities NTSA Booking", filters={"vehicle": self.vehicle, "name": ["!=", self.name], "status": "Planned"}, pluck="name"):
			frappe.db.set_value("Facilities NTSA Booking", name, "status", "Cancelled")

	def send_booking_confirmation(self):
		notify(
			self.vehicle,
			_("NTSA appointment booked for {0}").format(self.registration_number),
			_("{0} for vehicle {1} is booked for {2}{3}{4}. Booking reference: {5}.").format(
				_(self.service_type), self.registration_number, frappe.utils.formatdate(self.appointment_date),
				f" at {self.appointment_time}" if self.appointment_time else "",
				f", {self.inspection_centre}" if self.inspection_centre else "", self.booking_reference or "-"),
			self, extra_users=[self.booked_by],
		)

	def notify_failure(self):
		notify(
			self.vehicle,
			_("NTSA inspection failed: {0}").format(self.registration_number),
			_("Vehicle {0} did not pass inspection on {1}.<br><br><b>Reasons:</b> {2}<br><br>Raise a repair work order and book a re-inspection from the booking.").format(
				self.registration_number, frappe.utils.formatdate(self.result_date), frappe.utils.escape_html(self.failure_reasons or "")),
			self, extra_users=[self.booked_by],
		)


@frappe.whitelist()
def make_repair_work_order(booking):
	"""Raise a work order for the defects found at a failed inspection."""
	doc = frappe.get_doc("Facilities NTSA Booking", booking)
	doc.check_permission("write")
	if doc.status != "Failed":
		frappe.throw(_("A repair work order is raised for a failed inspection."))
	if doc.repair_work_order:
		frappe.throw(_("Repair work order {0} already exists.").format(doc.repair_work_order))
	asset = frappe.db.get_value("Facility Vehicle", doc.vehicle, "facility_asset")
	wo = frappe.get_doc({
		"doctype": "Facilities Work Order",
		"subject": _("Repairs after failed NTSA inspection: {0}").format(doc.registration_number),
		"work_order_type": "Corrective", "status": "Submitted", "priority": "High", "source": "Web Portal",
		"description": doc.failure_reasons, "facility_asset": asset, "cost_category": "Vehicle",
		"trade_category": "Other", "trade_other": "Vehicle repair",
	})
	wo.flags.ignore_permissions = True
	wo.insert()
	doc.db_set("repair_work_order", wo.name)
	doc.add_comment("Info", _("Repair work order {0} raised.").format(wo.name))
	return {"doctype": "Facilities Work Order", "name": wo.name}


@frappe.whitelist()
def make_reinspection(booking):
	"""Plan a re-inspection after a failure."""
	doc = frappe.get_doc("Facilities NTSA Booking", booking)
	doc.check_permission("write")
	if doc.status != "Failed":
		frappe.throw(_("A re-inspection is booked after a failed inspection."))
	new = frappe.get_doc({
		"doctype": "Facilities NTSA Booking", "vehicle": doc.vehicle, "service_type": "Re-inspection", "status": "Planned",
		"previous_booking": doc.name, "inspection_centre": doc.inspection_centre, "booked_by": frappe.session.user,
	})
	new.insert()
	return {"doctype": new.doctype, "name": new.name}
