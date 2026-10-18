// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["SLA Compliance"] = {
	filters: [
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nMedium\nLow",
		},
	],
};
