// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Response and Resolution Time"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -180),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "Technician\nWork Order Type\nPriority\nDepartment\nSource Channel\nMonth",
			default: "Technician",
			reqd: 1,
		},
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
		{
			fieldname: "assigned_to",
			label: __("Technician"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "work_order_type",
			label: __("Work Order Type"),
			fieldtype: "Select",
			options: "\nCorrective\nPreventive Maintenance\nRequest\nInspection",
		},
	],
};
