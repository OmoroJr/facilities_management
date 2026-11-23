// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['Facilities Ticket'] = {
	add_fields: ['status', 'priority'],
	get_indicator(doc) {
		const colors = {
			'Open': 'red', 'In Progress': 'orange', 'Waiting on Requester': 'yellow',
			'Resolved': 'green', 'Closed': 'gray',
		};
		return [__(doc.status), colors[doc.status] || 'gray', 'status,=,' + doc.status];
	},
};
