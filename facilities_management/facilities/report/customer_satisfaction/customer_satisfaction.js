// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Satisfaction"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -365),
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
			options: "Technician\nWork Order Type\nDepartment\nSource Channel\nMonth",
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
		{
			fieldname: "min_ratings",
			label: __("Minimum Ratings"),
			fieldtype: "Int",
			default: 0,
		},
	],
};
