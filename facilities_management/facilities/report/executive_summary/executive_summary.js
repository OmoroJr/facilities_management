// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Executive Summary"] = {
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
			fieldname: "work_order_type",
			label: __("Work Order Type"),
			fieldtype: "Select",
			options: "\nCorrective\nPreventive Maintenance\nRequest\nInspection",
		},
		{
			fieldname: "source",
			label: __("Source Channel"),
			fieldtype: "Select",
			options: "\nWeb Portal\nEmail\nWhatsApp\nPhone\nMobile App\nWalk-in",
		},
		{
			fieldname: "client_type",
			label: __("Client Type"),
			fieldtype: "Select",
			options: "\nInternal\nExternal",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "net_backlog_change" && data && data.net_backlog_change > 0) {
			value = "<span style='color:#E24C4C'>" + value + "</span>";
		}
		if (column.fieldname == "sla_pct" && data && data.sla_pct !== null && data.sla_pct < 75) {
			value = "<span style='color:#E24C4C'>" + value + "</span>";
		}
		return value;
	},
};
