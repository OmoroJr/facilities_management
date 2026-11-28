// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Work Order', {
	refresh(frm) {
		if (frm.doc.status && !frm.is_new()) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator-pill whitespace-nowrap orange">Status: ${frm.doc.status}</span>`
			);
		}
		const staff = frappe.user.has_role(['System Manager', 'Facilities Manager', 'Facilities Technician']);
		if (staff && !frm.is_new() && !frm.doc.acknowledged_on && frm.doc.status !== 'Draft') {
			frm.add_custom_button(__('Acknowledge Receipt'), () => {
				frappe.call({
					method: 'facilities_management.facilities.doctype.facilities_work_order.facilities_work_order.acknowledge',
					args: { work_order: frm.doc.name },
					freeze: true,
				}).then(() => frm.reload_doc());
			});
		}
		frm.set_query('policy_item', () => ({ filters: { is_active: 1 } }));
	},
	policy_item(frm) {
		if (!frm.doc.policy_item) return;
		frappe.db.get_value('Facilities Cost Policy Item', frm.doc.policy_item, 'cost_category')
			.then((r) => r.message && frm.set_value('cost_category', r.message.cost_category));
	},
	client_type(frm) {
		if (frm.doc.client_type === 'Internal') {
			frm.set_value('external_client_name', '');
		}
	},
});
