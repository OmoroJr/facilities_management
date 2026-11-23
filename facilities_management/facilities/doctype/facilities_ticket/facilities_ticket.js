// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Ticket', {
	refresh(frm) {
		if (frm.is_new()) return;

		const staff = frappe.user.has_role(['System Manager', 'Facilities Manager', 'Facilities Technician']);
		const open = ['Open', 'In Progress', 'Waiting on Requester'].includes(frm.doc.status);

		frm.dashboard.set_headline_alert(
			`<span class="indicator-pill whitespace-nowrap ${frm.events.indicator(frm.doc.status)}">${__(frm.doc.status)}</span>`
		);
		if (!staff) return;

		const set_status = (status, extra) => {
			frm.set_value(Object.assign({ status }, extra || {})).then(() => frm.save());
		};

		if (open && !frm.doc.linked_work_order) {
			frm.add_custom_button(__('Work Order'), () => {
				frappe.confirm(__('Raise a work order for this ticket?'), () => {
					frappe.call({
						method: 'facilities_management.facilities.doctype.facilities_ticket.facilities_ticket.make_work_order',
						args: { ticket: frm.doc.name },
						freeze: true,
					}).then((r) => {
						if (r.message) frappe.set_route('Form', 'Facilities Work Order', r.message);
					});
				});
			}, __('Create'));
		}

		if (frm.doc.status === 'Open') {
			frm.add_custom_button(__('Start Working'), () =>
				set_status('In Progress', frm.doc.assigned_to ? {} : { assigned_to: frappe.session.user }), __('Status'));
		}
		if (frm.doc.status === 'In Progress') {
			frm.add_custom_button(__('Waiting on Requester'), () => set_status('Waiting on Requester'), __('Status'));
		}
		if (frm.doc.status === 'Waiting on Requester') {
			frm.add_custom_button(__('Back In Progress'), () => set_status('In Progress'), __('Status'));
		}
		if (open) {
			frm.add_custom_button(__('Resolve'), () => {
				frappe.prompt(
					{ fieldname: 'notes', fieldtype: 'Text', label: __('Resolution Notes'), reqd: 1, default: frm.doc.resolution_notes },
					(v) => set_status('Resolved', { resolution_notes: v.notes }),
					__('Resolve Ticket'), __('Resolve')
				);
			}, __('Status'));
		}
		if (frm.doc.status === 'Resolved') {
			frm.add_custom_button(__('Close'), () => set_status('Closed'), __('Status'));
		}
		if (['Resolved', 'Closed'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Reopen'), () => set_status('Open'), __('Status'));
		}
	},

	indicator(status) {
		return {
			'Open': 'red', 'In Progress': 'orange', 'Waiting on Requester': 'yellow',
			'Resolved': 'green', 'Closed': 'gray',
		}[status] || 'gray';
	},

	client_type(frm) {
		if (frm.doc.client_type === 'Internal') frm.set_value('external_client_name', '');
	},
});
