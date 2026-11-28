// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Work Order Cost Allocation"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -365) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", reqd: 1, default: "Cost Category",
		  options: "Cost Category\nDepartment\nCharge Account / Cost Center\nApproval Method\nStatus" },
		{ fieldname: "cost_category", label: __("Cost Category"), fieldtype: "Select",
		  options: "\nGeneral Facilities Cost\nDepartment-Specific Cost\nShared / Exceptional Area\nVehicle\nEmergency" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
	],
};
