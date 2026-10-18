// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Completed Work Orders"] = {
	filters: [
		{
			fieldname: "assigned_to",
			label: __("Technician"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
	],
};
