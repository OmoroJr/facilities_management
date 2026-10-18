from . import __version__ as app_version

app_name = "facilities_management"
app_title = "Facilities Management"
app_publisher = "PingTap Solutions"
app_description = "Facilities Work Order, Asset, Maintenance, Booking, Vendor & Safety Management"
app_email = "info@pingtapsolutions.com"
app_license = "MIT"
app_icon = "octicon octicon-tools"
app_color = "#2e7d32"

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
	],
	"hourly": [
		"facilities_management.utils.scheduler.escalate_unassigned_work_orders",
		"facilities_management.utils.scheduler.notify_sla_breaches",
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
		],
	},
	"Facilities Work Order": {
		"after_insert": "facilities_management.utils.email_hooks.on_work_order_created",
		"on_update": "facilities_management.utils.email_hooks.on_work_order_assignment_change",
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
after_migrate = ["facilities_management.utils.setup.ensure_dashboard_assets"]

# Website
# ------------------
website_route_rules = [
	{"from_route": "/facilities-work-order-request", "to_route": "facilities-work-order-request"},
]
