import frappe

ROLES = ["Facilities Manager", "Facilities Staff", "Facilities Requester"]
M, S, R = "Facilities Manager", "Facilities Staff", "Facilities Requester"

# (state, style, role allowed to edit the document in that state)
WO_STATES = [
    ("Draft", "Warning", R), ("Submitted", "Info", S), ("Pending Approval", "Warning", M),
    ("Approved", "Success", M), ("Rejected", "Danger", R), ("Assigned", "Info", S),
    ("In Progress", "Primary", S), ("On Hold", "Warning", S), ("Completed", "Success", S),
    ("Closed", "Inverse", "System Manager"), ("Cancelled", "Danger", "System Manager"),
]
# (from, action, to, [roles])
WO_TRANSITIONS = [
    ("Draft", "Submit", "Submitted", [R, S, M]),
    ("Draft", "Cancel", "Cancelled", [R, M]),
    ("Submitted", "Send for Approval", "Pending Approval", [S, M]),
    ("Submitted", "Cancel", "Cancelled", [M]),
    ("Pending Approval", "Approve", "Approved", [M]),
    ("Pending Approval", "Reject", "Rejected", [M]),
    ("Pending Approval", "Cancel", "Cancelled", [M]),
    ("Rejected", "Reopen", "Draft", [R, M]),
    ("Approved", "Assign", "Assigned", [M]),
    ("Approved", "Cancel", "Cancelled", [M]),
    ("Assigned", "Start Work", "In Progress", [S, M]),
    ("Assigned", "Cancel", "Cancelled", [M]),
    ("In Progress", "Put On Hold", "On Hold", [S, M]),
    ("In Progress", "Complete", "Completed", [S, M]),
    ("On Hold", "Resume", "In Progress", [S, M]),
    ("On Hold", "Cancel", "Cancelled", [M]),
    ("Completed", "Close", "Closed", [M]),
    ("Completed", "Reopen", "In Progress", [M]),
]
VA_STATES = [("Draft", "Warning", S), ("Pending Approval", "Warning", M),
             ("Approved", "Success", "System Manager"), ("Rejected", "Danger", S)]
VA_TRANSITIONS = [
    ("Draft", "Submit for Approval", "Pending Approval", [S, M]),
    ("Pending Approval", "Approve", "Approved", [M]),
    ("Pending Approval", "Reject", "Rejected", [M]),
    ("Rejected", "Revise", "Draft", [S, M]),
]


def ensure_roles():
    for r in ROLES:
        if not frappe.db.exists("Role", r):
            frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)


def _make(name, doctype, states, transitions):
    if frappe.db.exists("Workflow", name):
        return
    for state, style, _role in states:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state,
                            "style": style}).insert(ignore_permissions=True)
    rows = []
    for frm, action, to, roles in transitions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master",
                            "workflow_action_name": action}).insert(ignore_permissions=True)
        for role in roles:
            rows.append({"state": frm, "action": action, "next_state": to, "allowed": role,
                         "allow_self_approval": 1})
    frappe.get_doc({
        "doctype": "Workflow", "workflow_name": name, "document_type": doctype, "is_active": 1,
        "workflow_state_field": "workflow_state", "send_email_alert": 0,
        "states": [{"state": s, "doc_status": "0", "allow_edit": role} for s, _st, role in states],
        "transitions": rows,
    }).insert(ignore_permissions=True)


def ensure_workflows():
    _make("Facilities Work Order Workflow", "Facilities Work Order", WO_STATES, WO_TRANSITIONS)
    _make("Vendor Approval Workflow", "Vendor Approval Request", VA_STATES, VA_TRANSITIONS)
