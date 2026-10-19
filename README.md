# Facilities Management

A Frappe/ERPNext app implementing the Aim International Facilities Work Order
Management requirements: work order ticketing, asset & preventive maintenance
management, room/vehicle resource booking, vendor management with approval
workflow, inventory alerts (via core Stock), and safety & compliance tracking.

## Install

	bench get-app facilities_management /path/to/facilities_management
	bench --site <site> install-app facilities_management
	bench --site <site> migrate

## Modules / DocTypes

See facilities_management/facilities/doctype for the full DocType list, and
facilities_management/hooks.py for scheduler jobs, notification wiring, and
document event hooks.

## Client request intake: Web, Email & WhatsApp

Facilities Work Order can be raised from three channels; all three land in
the same Draft -> Submitted -> ... workflow.

**Web portal** - no setup needed. `/facilities-work-order-request` is a
public Web Form (login required) that any Facilities Client can submit.

**Email** - uses Frappe's built-in inbound-email mechanism for the ticket
creation itself, plus a Facilities Settings toggle for everything after that:
1. Desk > Email Account > New. Point it (IMAP) at the facilities inbox.
2. Set "Append To" = `Facilities Work Order`, enable Incoming.
3. Save. New emails to that inbox create a Work Order (subject = email
   subject, `raised_by` = sender's address) - this part is core Frappe
   behaviour and always on once the Email Account is configured; replies
   thread onto the same ticket as Communications.
4. In Facilities Settings, tick **"Enable Email Request Intake"**. With it
   on, `utils/email_intake.py` runs once on the founding email: matches the
   sender against a System User (Internal) or not (External), fills
   `description` from the email body, auto-submits the ticket out of Draft
   into the approval queue, and (if "Send Acknowledgement Reply" is also
   ticked) emails the sender their ticket ID and tracking link.
   With it off, emails still create bare Draft tickets via step 3 (that part
   isn't gated - it's a DocType-level flag Frappe itself acts on) but they
   just sit there unenriched until someone manually reviews and submits
   them, so treat the setting as a way to hold intake for review rather
   than a hard stop on ticket creation.

## Ticket tracking (no login required)

`/track-ticket` is a public page - anyone with a ticket ID (e.g.
`WO-2026-00001`) and the email or phone number it was raised with can check
its status, without a portal account. This is mainly for Email/WhatsApp
requesters, who don't have one.

- Backed by `utils/tracking.py`'s `get_ticket_status` (a guest-whitelisted
  method), which only returns status/priority/dates/resolution notes - never
  internal fields like who it's assigned to.
- The ticket ID + contact must both match, and a wrong guess gives the same
  generic "not found" message as a wrong ID, so the endpoint can't be used
  to enumerate tickets. It's also rate-limited per IP (15 attempts / 5 min).
- The link is included automatically in the email acknowledgement above and
  in the WhatsApp acknowledgement reply; it's also in the portal sidebar
  ("Track a Ticket") for anyone who is logged in but prefers not to dig
  through the list view.

## Dashboard

A standard Frappe Dashboard ("Facilities") ships with the app - Desk >
Dashboards > Facilities, or directly at `/app/dashboard-view/Facilities`.

**Number Cards** (6): Open Work Orders, Pending Approval, Completed Work
Orders (with month-over-month %), Pending Vendor Approvals, Active PM
Schedules, Safety Inspections Needing Attention.

**Charts** (4): Work Orders by Status (donut), Work Orders by Priority
(bar), Work Orders Created - Monthly (line trend), Safety Inspections by
Status (donut).

All are plain "Document Type" cards and "Group By"/"Count" charts built
from static filters - no custom Python behind them, so they're editable
from the Desk UI (Customize > Number Card / Dashboard Chart) the same way
any standard Frappe dashboard is, if you want to add more or adjust the
groupings.

**WhatsApp** - uses Meta's WhatsApp Cloud API directly (no third-party app):
1. In Facilities Settings, tick "Enable WhatsApp Request Intake" and fill in
   Phone Number ID, a Cloud API Access Token, and a Webhook Verify Token
   (any string you choose).
2. In the Meta App Dashboard (WhatsApp > Configuration): set the Webhook URL
   to `https://<your-site>/api/method/facilities_management.utils.whatsapp.webhook`,
   set the Verify Token to match step 1, and subscribe to the `messages`
   field.
3. Incoming messages create a Work Order (`source` = WhatsApp, matched
   against Employee by phone number for Internal vs External, auto-submitted
   the same way as email); each is logged once in **WhatsApp Message Log**
   for idempotency, since Meta redelivers on timeout.
4. Optional: "Send Acknowledgement Reply" sends a free-form WhatsApp
   confirmation back (ticket ID + tracking link) - note Meta only allows
   free-form replies within its 24-hour customer-service window, so anything
   later needs a pre-approved template (not implemented here).

## Email hooks (v0.0.2)

| Trigger | Who is emailed |
|---|---|
| Work Order created | Facilities Managers + default approver |
| Status -> Pending Approval / Assigned / Approved / In Progress / Completed / Closed / Rejected | approver / assignee / requester (external requesters via their raised-by address, with tracking link) |
| Assignee changed without a status change | new assignee |
| Customer replies by email on an existing ticket | assignee, or managers if unassigned |
| Customer replies on a Completed/Closed ticket | ticket is reopened (Assigned if it has a technician, else Approved); assignee/managers are told |
| Room/Vehicle Booking created / confirmed / re-timed / cancelled | the person who booked, with a `.ics` calendar invite (confirm/update) or cancellation |
| "Send Calendar Invite" button on a Confirmed booking (Actions menu; reached by clicking an event in the calendar view) | any emails you enter, or the person who booked if left blank; each gets the `.ics` and a note is logged on the booking |
| Internal comment on a ticket | assignee |
| SLA due date passed (hourly job, once per ticket) | Facilities Managers + assignee |

Each alert group has a toggle in Facilities Settings -> Email Alerts. Bounces and auto-replies never trigger an acknowledgement.

## Dashboard
11 charts and 6 number cards on the Facilities workspace and the Facilities dashboard. `after_migrate` re-asserts them from the app's JSON; failures show in Error Log as "Facilities: could not set up ...".

## Enterprise reports and analytics (v0.0.3)

Every report now has a filter screen; the nine new ones have a KPI summary strip, a chart and drill-down tables.

| Report | What it answers |
|---|---|
| Executive Summary | Monthly created vs completed, backlog, SLA %, response/resolution time, rating |
| Work Order Aging | Open tickets by age bucket and hours past SLA |
| Response and Resolution Time | Avg/median/slowest by technician, type, priority, department, channel or month |
| Customer Satisfaction | Avg rating, CSAT %, response rate, star distribution |
| Asset Lifecycle and Warranty | Age, warranty state, service recency, next PM, repeat-failure assets |
| Spend Analysis | PO spend by vendor, month, asset category, status or requester |
| Resource Utilization | Room/vehicle booked hours vs available hours, with utilization bands |
| Vendor Scorecard | Contracts, expiry exposure, PO spend, fulfilment and share per vendor |
| Maintenance Mix | Preventive vs corrective vs inspection work, planned-work % |

Dashboard additions: 5 number cards (Overdue Work Orders, SLA Compliance 30 Days, Avg Resolution Hours 30 Days, Warranties Expiring 90 Days, Contracts Expiring 60 Days; backed by `facilities_management.api.dashboard`) and 7 report-driven charts. Ratings are shown on a 1-5 scale. Reports are visible to Facilities Manager, Facilities Approver and System Manager.
