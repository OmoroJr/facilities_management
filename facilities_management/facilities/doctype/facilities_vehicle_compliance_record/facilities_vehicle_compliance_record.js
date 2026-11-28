// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Vehicle Compliance Record', {
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		frappe.db.get_value('Facility Vehicle', frm.doc.vehicle, ['insurance_provider', 'insurance_policy_number', 'governor_speed_limit']).then((r) => {
			const v = r.message || {};
			if (frm.doc.compliance_type === 'Insurance' && !frm.doc.provider && v.insurance_provider) frm.set_value('provider', v.insurance_provider);
			if (frm.doc.compliance_type === 'Speed Governor' && !frm.doc.speed_limit_kph && v.governor_speed_limit) frm.set_value('speed_limit_kph', v.governor_speed_limit);
		});
	},
});
