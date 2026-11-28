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


## Ticketing (v0.0.7)

`Facilities Ticket` (TKT-YYYY-#####) is the front door for anything someone reports - a leak, a lock,
a question - while `Facilities Work Order` stays the approved job on the ground. Most tickets are fixed
by replying; when a technician has to go and do something, **Create > Work Order** raises one from
the ticket and the two stay linked (completing/closing the work order resolves/closes the ticket).

* Statuses: Open > In Progress > Waiting on Requester > Resolved > Closed (resolve needs notes;
  Resolved tickets auto-close after *Auto-close Resolved Tickets After (days)* in Facilities Settings).
* **Facilities Ticket Category** sets a default assignee/priority and optional first-response and
  resolution targets per category (starter categories are added on migrate). Without an override,
  targets come from the priority: first response 1/4/8/24 h, resolution 4/24/72/168 h
  (Critical/High/Medium/Low). Hourly job alerts once on a missed response and once on a missed resolution;
  the clock is paused while a ticket is Waiting on Requester.
* Email: point the Email Account's **Append To** at *Facilities Ticket* (and keep *Enable Email Request
  Intake* ticked in Facilities Settings). The first email creates the ticket and is acknowledged with the
  ticket ID + tracking link; replies thread onto it, move Waiting > In Progress and reopen Resolved/Closed
  tickets (*Reopen on reply* setting).
* `/track-ticket` accepts both TKT- and WO- IDs.
* Requesters (role Facilities Client) can log and view their own tickets under /app/facilities-ticket
  but cannot change status, priority, category or assignment.


## ABS Work Order Procedure Manual alignment (v0.0.8)

The system now follows the ABS Work Order Procedure Manual (draft Rv 17-12-2025) end to end.

| Manual step | Where it lives |
|---|---|
| 1 Identify and report | Facilities Ticket (portal, email, phone, walk-in) |
| 2 Vetting and segmentation | Priority and SLA; **Cost Category** and **Policy Item** on the work order (Facilities Cost Policy Item holds the ABS Cost Management Policy) |
| 3 Department approval | Approval workflow; for Department-Specific and Shared costs approval needs a charge account / cost center, how approval was given (Email, Signed Form or System Approval, never WhatsApp), the evidence, and cost sharing agreed |
| 4 Submission and 24-hour acknowledgement | *Acknowledged On* is stamped when Facilities first acts; **Acknowledge Receipt** button; hourly alert to Facilities Managers if a Submitted work order is not acknowledged within *Acknowledge Work Orders Within (hours)* |
| 5 Quotation | Quotation attachment, materials / labour / transport / other, total and duration on the work order; purchase orders require an approved quotation |
| 6 Scheduling | Proposed dates, assignment, preventive maintenance; optional **signed contract required** before work starts |
| 7 Execution | Start, hold, complete with timestamps; technician / contractor details |
| 8 Review and feedback | Written client confirmation (who, when, how, attachment), client feedback, provider feedback and rating |
| 9 Close | Needs the client confirmation and a Facilities inspection (switch off with *Require Written Completion Confirmation*). Final payment approval needs the inspection and the confirmation or a warranty. Auto-close only closes confirmed, inspected work orders |
| Emergencies | Emergency category or Critical priority skips the pre-approval documentation; Facilities Manager has an **Emergency Approve** action |

Purchase orders add justification, delivery, VAT, payment option details, Facilities review, **Finance Approve**
(Accounts Manager), supplier acknowledgement, goods receipt confirmation and delivery note/invoice attachments.
Maintenance contracts add scope, cost split, deposit, warranty, signatures and a signed copy.

Print formats: **ABS Maintenance Work Order Form**, **ABS Purchase Order**, **ABS Maintenance Contract**.
Report: **Work Order Cost Allocation** (who is paying, by cost category, department, charge account or status).
Staff-only fields on the work order sit at permission level 1; requesters can still fill the form, contact details and
the completion confirmation.


## NTSA vehicle inspection (v0.0.9)

Tracks the NTSA inspection of every Facility Vehicle, books appointments and reminds people before it lapses.

* **Facility Vehicle** has an *NTSA Compliance* section: inspection required, last inspection, due / certificate
  expiry, certificate number and a computed **NTSA Status** (Valid, Due Soon, Overdue, Not Required, Unknown).
  Enter the due date once; after that it is updated by the bookings.
* **Facilities NTSA Booking** (NTSA-YYYY-#####): Planned > Booked > Passed / Failed / Cancelled. Booking needs an
  appointment date; recording a pass needs the inspection date, certificate number and expiry and then resets the
  vehicle's due date; recording a failure needs the defects and offers **Create > Repair Work Order** (cost category
  Vehicle) and **Create > Re-inspection Booking**.
* **Reminders** (daily job, email to Facilities Managers, the vehicle's driver and whoever booked): before due on the
  days in *Remind Before Due* (default 30, 14, 7, 3, 1), on the due day, the day after it lapses and then every
  7 days; before an appointment (default 3, 1 and 0 days); and after an appointment that has no result recorded
  (1, 3 and 7 days). A vehicle already booked in time is not nagged about the due date.
* **Planned bookings are created automatically** 30 days before the due date (switch off in Facilities Settings).
* **Vehicle Booking** warns when the vehicle's inspection has expired before the trip; tick *Block Vehicle Bookings
  When NTSA Inspection Has Expired* to stop the booking instead.
* Dashboard: *NTSA Due Soon*, *NTSA Overdue*, *NTSA Inspections Booked* and *Vehicles by NTSA Status*; report
  **Vehicle NTSA Compliance**; Facilities workspace shortcuts.

The system does not connect to NTSA or eCitizen. The appointment is booked on the NTSA / eCitizen site and
recorded here with its reference.


## Insurance and speed governor tracking (v0.0.10)

Every Facility Vehicle now keeps three things valid, each with its own status: **NTSA inspection**, **Insurance**
and **Speed Governor**.

* Vehicle fields: *Insurance Required* (on by default), insurer, policy number, cover expiry; *Speed Governor Required*
  (off by default, tick it for vehicles that need one), certificate number, speed limit and certificate expiry.
  Enter the expiry dates once; the first time a vehicle is saved its statuses are calculated.
* **Facilities Vehicle Compliance Record** (VCR-YYYY-#####) records each insurance renewal or speed governor
  certification with provider, policy / certificate number, cover type, dates, premium or fee, payment reference and
  the document. Saving a record makes it the vehicle's current cover or certificate when it runs later than the one on
  file, and recalculates the status. An older record is kept as history and does not change the vehicle.
* Reminders use the same days and repeat setting as the NTSA inspection (Facilities Settings > Vehicle Compliance):
  before expiry, on the day, the day after it lapses and then every 7 days. Emails go to Facilities Managers and the
  vehicle's driver. There is no booking step for insurance or the speed governor.
* **Vehicle Booking** warns, or blocks if *Block Vehicle Bookings When Insurance, NTSA Inspection or Speed Governor Has
  Expired* is ticked, when any of the three has expired before the trip.
* Dashboard: *Vehicles With Expired Compliance*. Report: **Vehicle Compliance Register** (one row per vehicle per item,
  filterable by item, status and vehicle type). Facilities workspace shortcuts for Compliance Records and the register.
