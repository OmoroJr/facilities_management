// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Maintenance History"] = {
	filters: [
		{
			fieldname: "facility_asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Facility Asset",
		},
	],
};
