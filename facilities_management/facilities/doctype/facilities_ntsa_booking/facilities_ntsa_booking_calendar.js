// Copyright (c) 2026, PingTap Solutions and contributors
// For license information, please see license.txt

frappe.views.calendar['Facilities NTSA Booking'] = {
	field_map: { start: 'appointment_date', end: 'appointment_date', id: 'name', title: 'registration_number', allDay: 'allDay' },
	get_events_method: 'frappe.desk.calendar.get_events',
};
