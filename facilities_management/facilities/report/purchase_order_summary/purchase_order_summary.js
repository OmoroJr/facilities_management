// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Order Summary"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nPending Approval\nApproved\nOrdered\nReceived\nCancelled",
		},
		{
			fieldname: "vendor",
			label: __("Vendor"),
			fieldtype: "Link",
			options: "Supplier",
		},
	],
};
