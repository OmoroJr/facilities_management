// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Preventive Maintenance Compliance"] = {
	filters: [
		{
			fieldname: "facility_asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Facility Asset",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nPaused\nCompleted",
		},
	],
};
