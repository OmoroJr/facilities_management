// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Resource Booking Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nRequested\nConfirmed\nCancelled\nCompleted",
		},
	],
};
