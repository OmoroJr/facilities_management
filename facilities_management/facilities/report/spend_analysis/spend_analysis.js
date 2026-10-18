// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Spend Analysis"] = {
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
			options: "Vendor\nMonth\nAsset Category\nStatus\nRequested By",
			default: "Vendor",
			reqd: 1,
		},
		{
			fieldname: "vendor",
			label: __("Vendor"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nApproved\nOrdered\nReceived\nPending Approval",
		},
	],
};
