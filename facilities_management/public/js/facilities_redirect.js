// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

// The Facilities workspace lives at /desk/facilities. Frappe also generates an
// app page at /desk/facilities-management (a plain list of doctypes); send
// anyone who lands there to the real workspace.
(function () {
	const OLD = "facilities-management";
	const NEW = "facilities";

	function redirect_if_needed() {
		const parts = window.location.pathname.split("/").filter(Boolean);
		if (parts.length === 2 && parts[0] === "desk" && parts[1] === OLD) {
			frappe.set_route(NEW);
		}
	}

	$(document).on("startup", redirect_if_needed);
	$(function () {
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", redirect_if_needed);
		}
	});
})();
