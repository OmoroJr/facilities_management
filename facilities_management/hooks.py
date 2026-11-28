from . import __version__ as app_version

app_name = "facilities_management"
app_title = "Facilities Management"
app_publisher = "PingTap Solutions"
app_description = "Facilities Work Order, Asset, Maintenance, Booking, Vendor & Safety Management"
app_email = "info@pingtapsolutions.com"
app_license = "MIT"
app_icon = "octicon octicon-tools"
app_color = "#2e7d32"

# Apps screen tile -> opens the Facilities workspace at /desk/facilities
add_to_apps_screen = [
	{
		"name": "facilities_management",
		"logo": "/assets/facilities_management/images/facilities-logo.svg",
		"title": "Facilities Management",
		"route": "/desk/facilities",
	}
]

# Send /desk/facilities-management to /desk/facilities
app_include_js = ["/assets/facilities_management/js/facilities_redirect.js"]

# Fixtures
# ------------------
fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"Facilities Manager",
					"Facilities Technician",
					"Facilities Approver",
					"Facilities Client",
				],
			]
		],
	}
]

# Scheduled Tasks
# ------------------
scheduler_events = {
	"daily": [
		"facilities_management.utils.scheduler.generate_due_preventive_maintenance",
		"facilities_management.utils.scheduler.check_contract_renewals",
		"facilities_management.utils.scheduler.check_certification_expiries",
		"facilities_management.utils.scheduler.auto_close_completed_work_orders",
		"facilities_management.utils.ticketing.auto_close_resolved_tickets",
		"facilities_management.utils.ntsa.daily_ntsa_checks",
	],
	"hourly": [
		"facilities_management.utils.scheduler.escalate_unassigned_work_orders",
		"facilities_management.utils.scheduler.notify_sla_breaches",
		"facilities_management.utils.ticketing.check_ticket_sla",
		"facilities_management.utils.procedure.check_acknowledgement_overdue",
	],
}

# Portal
# ------------------
standard_portal_menu_items = [
	{
		"title": "Facilities Requests",
		"route": "/facilities-work-order-request",
		"reference_doctype": "Facilities Work Order",
		"role": "Facilities Client",
	},
	{
		"title": "Support Tickets",
		"route": "/app/facilities-ticket",
		"reference_doctype": "Facilities Ticket",
		"role": "Facilities Client",
	},
	{
		"title": "Track a Ticket",
		"route": "/track-ticket",
	},
	{
		"title": "Room Bookings",
		"route": "/app/room-booking",
		"reference_doctype": "Room Booking",
		"role": "Facilities Client",
	},
	{
		"title": "Vehicle Bookings",
		"route": "/app/vehicle-booking",
		"reference_doctype": "Vehicle Booking",
		"role": "Facilities Client",
	},
]

# Document Events
# ------------------
# Ticketing (Facilities Ticket): utils/ticketing.py handles inbound/outbound ticket email,
# keeps a ticket in step with its linked work order, and runs the SLA/auto-close jobs.
# Status-change mail (Pending Approval / Assigned / Completed ...) is sent from
# the Facilities Work Order controller via utils/notifications.py. The hooks
# below add the cross-document email behaviour:
#   - Communication: enrich + acknowledge the founding email (email_intake),
#     and forward later customer replies to the assignee (email_hooks)
#   - Facilities Work Order: new-ticket alert, assignee-change mail
#   - Comment: internal comments on a ticket reach the assignee
doc_events = {
	"Communication": {
		"after_insert": [
			"facilities_management.utils.email_intake.on_communication_insert",
			"facilities_management.utils.email_hooks.notify_on_ticket_reply",
			"facilities_management.utils.ticketing.on_communication_insert",
		],
	},
	"Facilities Work Order": {
		"after_insert": "facilities_management.utils.email_hooks.on_work_order_created",
		"on_update": [
			"facilities_management.utils.email_hooks.on_work_order_assignment_change",
			"facilities_management.utils.ticketing.sync_ticket_from_work_order",
		],
	},
	"Room Booking": {
		"on_update": "facilities_management.utils.booking_invites.send_booking_email",
	},
	"Vehicle Booking": {
		"on_update": "facilities_management.utils.booking_invites.send_booking_email",
	},
	"Comment": {
		"after_insert": "facilities_management.utils.email_hooks.notify_on_ticket_comment",
	},
}

# Calendar view availability for the booking doctypes
calendars = ["Room Booking", "Vehicle Booking"]

# Re-assert dashboard cards/charts/workspace blocks after every migrate
after_migrate = ["facilities_management.utils.setup.after_migrate"]

# Website
# ------------------
website_route_rules = [
	{"from_route": "/facilities-work-order-request", "to_route": "facilities-work-order-request"},
]
