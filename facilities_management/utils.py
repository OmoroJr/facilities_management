import frappe
from frappe import _
from frappe.utils import get_datetime


def get_settings():
    return frappe.get_cached_doc("Facilities Settings")


def notify(recipients, subject, message, doctype=None, name=None, phone=None):
    """Send email and/or SMS depending on Facilities Settings. Never raises."""
    try:
        s = get_settings()
        recipients = sorted({r for r in (recipients or []) if r})
        if s.enable_email_notifications and recipients:
            frappe.sendmail(recipients=recipients, subject=subject, message=message,
                            reference_doctype=doctype, reference_name=name)
        if s.enable_sms_notifications and s.sms_gateway_url and phone:
            import requests
            token = s.get_password("sms_auth_token", raise_exception=False) or ""
            requests.post(s.sms_gateway_url,
                          json={"to": phone, "message": subject, "sender": s.sms_sender_id},
                          headers={"Authorization": "Bearer " + token}, timeout=10)
    except Exception:
        frappe.log_error(title="Facilities notification failed")


def check_overlap(doc, resource_field, label):
    """Throw if another non-cancelled booking of the same resource overlaps this one."""
    if doc.status == "Cancelled":
        return
    if get_datetime(doc.end_datetime) <= get_datetime(doc.start_datetime):
        frappe.throw(_("End time must be after start time."))
    clash = frappe.get_all(
        doc.doctype,
        filters=[[resource_field, "=", doc.get(resource_field)],
                 ["name", "!=", doc.name or ""],
                 ["status", "!=", "Cancelled"],
                 ["start_datetime", "<", doc.end_datetime],
                 ["end_datetime", ">", doc.start_datetime]],
        fields=["name", "start_datetime", "end_datetime"], limit=1)
    if clash:
        c = clash[0]
        frappe.throw(_("{0} is already booked from {1} to {2} ({3}).").format(
            label, frappe.format(c.start_datetime, "Datetime"), frappe.format(c.end_datetime, "Datetime"), c.name))
