// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Facilities Low Stock Alerts"] = {
	filters: [
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
	],
};
