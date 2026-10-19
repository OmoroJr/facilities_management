// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Safety Inspection Compliance"] = {
	filters: [
		{
			fieldname: "inspection_type",
			label: __("Inspection Type"),
			fieldtype: "Select",
			options: "\nFire Safety\nElectrical Safety\nEquipment Safety\nEnvironmental\nOther",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nPassed\nFailed\nNeeds Attention",
		},
	],
};
