// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.views.calendar["Room Booking"] = {
	field_map: {
		start: "from_datetime",
		end: "to_datetime",
		id: "name",
		title: "room",
		status: "status",
	},
	// colour each booking by status
	get_css_class: function (data) {
		const map = {
			Requested: "warning",
			Confirmed: "success",
			Completed: "default",
			Cancelled: "danger",
		};
		return map[data.status] || "default";
	},
	order_by: "from_datetime",
	filters: [
		{
			fieldtype: "Link",
			fieldname: "room",
			options: "Facility Room",
			label: __("Room"),
		},
		{
			fieldtype: "Select",
			fieldname: "status",
			options: "\nRequested\nConfirmed\nCancelled\nCompleted",
			label: __("Status"),
		},
	],
};
