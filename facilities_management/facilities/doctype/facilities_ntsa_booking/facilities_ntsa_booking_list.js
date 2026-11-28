// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['Facilities NTSA Booking'] = {
	add_fields: ['status'],
	get_indicator(doc) {
		const colors = { Planned: 'orange', Booked: 'blue', Passed: 'green', Failed: 'red', Cancelled: 'gray' };
		return [__(doc.status), colors[doc.status] || 'gray', 'status,=,' + doc.status];
	},
};
