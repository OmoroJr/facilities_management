// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Work Order Aging"] = {
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
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nPending Approval\nApproved\nAssigned\nIn Progress\nOn Hold",
		},
		{
			fieldname: "overdue_only",
			label: __("Overdue Only"),
			fieldtype: "Check",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.overdue_hrs > 0 && ["overdue_hrs", "sla_state"].includes(column.fieldname)) {
			value = "<span style='color:#E24C4C;font-weight:600'>" + value + "</span>";
		}
		if (data && data.age_days > 30 && column.fieldname == "age_bucket") {
			value = "<span style='color:#E24C4C;font-weight:600'>" + value + "</span>";
		}
		return value;
	},
};
