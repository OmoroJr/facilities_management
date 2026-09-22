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
# NOTE: Facilities Work Order, Vendor Approval Request, Safety Inspection and
# Preventive Maintenance Schedule already trigger their own side effects
# (notifications, auto-record creation) from within their own controllers
# (see each doctype's .py file), so no additional doc_events wiring is
# required here. Add entries below only for cross-doctype hooks.
doc_events = {}

# Website
# ------------------
website_route_rules = [
	{"from_route": "/facilities-work-order-request", "to_route": "facilities-work-order-request"},
]
