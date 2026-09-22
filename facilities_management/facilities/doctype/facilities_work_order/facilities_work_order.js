// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Work Order', {
	refresh(frm) {
		if (frm.doc.status && !frm.is_new()) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator-pill whitespace-nowrap orange">Status: ${frm.doc.status}</span>`
			);
		}
	},
	client_type(frm) {
		if (frm.doc.client_type === 'Internal') {
			frm.set_value('external_client_name', '');
		}
	},
});
