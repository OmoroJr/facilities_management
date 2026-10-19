// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Resource Utilization"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "resource_type",
			label: __("Resource Type"),
			fieldtype: "Select",
			options: "\nRoom\nVehicle",
		},
		{
			fieldname: "hours_per_day",
			label: __("Available Hours per Day"),
			fieldtype: "Float",
			default: 8,
		},
		{
			fieldname: "include_weekends",
			label: __("Include Sundays"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_requested",
			label: __("Count Unconfirmed (Requested) Bookings"),
			fieldtype: "Check",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname == "band") {
			const c = {"Over-subscribed": "#E24C4C", "Idle": "#9AA0A6", "Under-used": "#F5A623", "Healthy": "#29A745"}[data.band];
			if (c) value = "<span style='color:" + c + ";font-weight:600'>" + value + "</span>";
		}
		return value;
	},
};
