// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['Facilities Vehicle Compliance Record'] = {
	add_fields: ['expiry_date'],
	get_indicator(doc) {
		const left = frappe.datetime.get_diff(doc.expiry_date, frappe.datetime.get_today());
		if (left < 0) return [__('Expired'), 'red', 'expiry_date,<,Today'];
		if (left <= 30) return [__('Expires Soon'), 'orange', 'expiry_date,Timespan,next month'];
		return [__('Valid'), 'green', 'expiry_date,>,Today'];
	},
};
