// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Lifecycle and Warranty"] = {
	filters: [
		{
			fieldname: "asset_category",
			label: __("Category"),
			fieldtype: "Select",
			options: "\nHVAC\nElevator\nElectrical\nPlumbing\nGenerator\nFire Safety\nIT Equipment\nFurniture\nVehicle\nOther",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nIn Service\nUnder Maintenance\nDecommissioned\nDisposed",
		},
		{
			fieldname: "criticality",
			label: __("Criticality"),
			fieldtype: "Select",
			options: "\nLow\nMedium\nHigh",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "vendor",
			label: __("Vendor"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "warranty_state",
			label: __("Warranty State"),
			fieldtype: "Select",
			options: "\nUnder Warranty\nExpiring (90 days)\nExpired\nNo Warranty Info",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname == "warranty_state") {
			const c = {"Expired": "#E24C4C", "Expiring (90 days)": "#F5A623", "Under Warranty": "#29A745"}[data.warranty_state];
			if (c) value = "<span style='color:" + c + ";font-weight:600'>" + value + "</span>";
		}
		if (data && data.repeat_failure && column.fieldname == "repeat_failure") {
			value = "<span style='color:#E24C4C;font-weight:600'>" + value + "</span>";
		}
		return value;
	},
};
