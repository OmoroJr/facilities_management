import frappe

from facilities_management.setup.workflows import ensure_roles, ensure_workflows

QUEUES = ["General", "Electrical", "Plumbing", "HVAC", "Cleaning", "Security", "IT & Equipment", "Grounds"]


def after_install():
    ensure_roles()
    ensure_workflows()
    for q in QUEUES:
        if not frappe.db.exists("Facilities Queue", q):
            frappe.get_doc({"doctype": "Facilities Queue", "queue_name": q, "is_active": 1}).insert(
                ignore_permissions=True)
    frappe.get_doc("Facilities Settings").save(ignore_permissions=True)  # persist defaults


def after_migrate():
    ensure_roles()
    ensure_workflows()
