// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Purchase Order', {
	refresh(frm) {
		const finance = frappe.user.has_role(['Accounts Manager', 'System Manager']);
		if (finance && !frm.is_new() && !frm.doc.finance_approved_on && ['Pending Approval', 'Approved'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Finance Approve'), () => {
				frappe.confirm(__('Confirm that funds are available and approve this purchase?'), () => {
					frappe.call({
						method: 'facilities_management.facilities.doctype.facilities_purchase_order.facilities_purchase_order.finance_approve',
						args: { purchase_order: frm.doc.name },
						freeze: true,
					}).then(() => frm.reload_doc());
				});
			});
		}
	},
	vat_amount(frm) {
		frm.set_value('grand_total', (frm.doc.total_amount || 0) + (frm.doc.vat_amount || 0));
	},
});
