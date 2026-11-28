// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facility Vehicle', {
	refresh(frm) {
		if (frm.is_new()) return;
		const colors = { Valid: 'green', 'Due Soon': 'orange', Overdue: 'red', 'Not Required': 'gray', Unknown: 'gray' };
		const pill = (label, status) => status ? `<span class="indicator-pill whitespace-nowrap ${colors[status] || 'gray'}">${label}: ${__(status)}</span>&nbsp;` : '';
		frm.dashboard.set_headline_alert(
			pill('NTSA', frm.doc.ntsa_status) + pill(__('Insurance'), frm.doc.insurance_status) + pill(__('Speed Governor'), frm.doc.governor_status)
		);
		frm.add_custom_button(__('NTSA Booking'), () => frappe.new_doc('Facilities NTSA Booking', { vehicle: frm.doc.name }), __('Create'));
		frm.add_custom_button(__('Insurance Renewal'), () => frappe.new_doc('Facilities Vehicle Compliance Record', { vehicle: frm.doc.name, compliance_type: 'Insurance' }), __('Create'));
		frm.add_custom_button(__('Speed Governor Certificate'), () => frappe.new_doc('Facilities Vehicle Compliance Record', { vehicle: frm.doc.name, compliance_type: 'Speed Governor' }), __('Create'));
		frm.add_custom_button(__('NTSA Bookings'), () => frappe.set_route('List', 'Facilities NTSA Booking', { vehicle: frm.doc.name }), __('View'));
		frm.add_custom_button(__('Compliance Records'), () => frappe.set_route('List', 'Facilities Vehicle Compliance Record', { vehicle: frm.doc.name }), __('View'));
	},
});
