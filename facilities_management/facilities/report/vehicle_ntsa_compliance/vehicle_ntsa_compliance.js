// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle NTSA Compliance"] = {
	filters: [
		{ fieldname: "ntsa_status", label: __("NTSA Status"), fieldtype: "Select", options: "\nValid\nDue Soon\nOverdue\nNot Required\nUnknown" },
		{ fieldname: "vehicle_type", label: __("Vehicle Type"), fieldtype: "Select", options: "\nCar\nVan\nTruck\nMotorbike\nOther" },
		{ fieldname: "include_not_required", label: __("Include Vehicles Not Requiring Inspection"), fieldtype: "Check", default: 0 },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "ntsa_status" && data) {
			const c = { Valid: "green", "Due Soon": "orange", Overdue: "red" }[data.ntsa_status];
			if (c) value = `<span class="indicator-pill ${c}">${data.ntsa_status}</span>`;
		}
		return value;
	},
};
