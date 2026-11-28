// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Compliance Register"] = {
	filters: [
		{ fieldname: "item", label: __("Item"), fieldtype: "Select", options: "\nNTSA Inspection\nInsurance\nSpeed Governor" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nValid\nDue Soon\nOverdue\nUnknown" },
		{ fieldname: "vehicle_type", label: __("Vehicle Type"), fieldtype: "Select", options: "\nCar\nVan\nTruck\nMotorbike\nOther" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const c = { Valid: "green", "Due Soon": "orange", Overdue: "red" }[data.status];
			if (c) value = `<span class="indicator-pill ${c}">${data.status}</span>`;
		}
		return value;
	},
};
