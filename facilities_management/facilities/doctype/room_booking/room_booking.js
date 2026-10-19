// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Booking", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Confirmed") return;

		frm.add_custom_button(__("Send Calendar Invite"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Send Calendar Invite"),
				fields: [
					{
						fieldname: "recipients",
						fieldtype: "Small Text",
						label: __("Send To"),
						description: __("Comma separated emails. Leave blank to send to the person who booked."),
					},
					{ fieldname: "message", fieldtype: "Small Text", label: __("Personal Message (optional)") },
				],
				primary_action_label: __("Send Invite"),
				primary_action(values) {
					frappe.call({
						method: "facilities_management.utils.booking_invites.send_invite",
						args: { doctype: frm.doctype, name: frm.doc.name, ...values },
						freeze: true,
						freeze_message: __("Sending invite..."),
						callback(r) {
							if (!r.exc) {
								d.hide();
								frappe.show_alert({
									message: __("Invite sent to {0}", [(r.message || []).join(", ")]),
									indicator: "green",
								});
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		}, __("Actions"));
	},
});
