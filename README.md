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

**Email** - uses Frappe's built-in inbound-email mechanism, no custom code
to configure:
1. Desk > Email Account > New. Point it (IMAP) at the facilities inbox.
2. Set "Append To" = `Facilities Work Order`, enable Incoming.
3. Save. New emails to that inbox create a Work Order (subject = email
   subject, `raised_by` = sender's address); replies thread onto the same
   ticket as Communications.
4. `utils/email_intake.py` then runs once, on the founding email only: it
   matches the sender against a System User (Internal) or not (External),
   fills `description` from the email body, and auto-submits the ticket
   out of Draft into the approval queue.

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
   confirmation back - note Meta only allows free-form replies within its
   24-hour customer-service window, so anything later needs a pre-approved
   template (not implemented here).
