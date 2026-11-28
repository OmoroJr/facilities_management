// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities NTSA Booking', {
	refresh(frm) {
		if (frm.is_new()) return;
		const base = 'facilities_management.facilities.doctype.facilities_ntsa_booking.facilities_ntsa_booking.';
		const call = (method, label, args) => frappe.call({ method: base + method, args, freeze: true, freeze_message: label })
			.then((r) => r.message && frappe.set_route('Form', r.message.doctype, r.message.name));

		if (['Planned', 'Booked'].includes(frm.doc.status)) {
			if (frm.doc.status === 'Planned') {
				frm.add_custom_button(__('Mark as Booked'), () => frm.set_value('status', 'Booked').then(() => frm.save()), __('Status'));
			}
			frm.add_custom_button(__('Cancel Booking'), () => frm.set_value('status', 'Cancelled').then(() => frm.save()), __('Status'));
		}
		if (frm.doc.status === 'Failed') {
			if (!frm.doc.repair_work_order) {
				frm.add_custom_button(__('Repair Work Order'), () => call('make_repair_work_order', __('Raising work order...'), { booking: frm.doc.name }), __('Create'));
			}
			frm.add_custom_button(__('Re-inspection Booking'), () => call('make_reinspection', __('Creating booking...'), { booking: frm.doc.name }), __('Create'));
		}
	},
});
