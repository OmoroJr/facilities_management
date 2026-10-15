# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""Idempotent re-assertion of the Facilities dashboard assets.

Standard Number Cards / Dashboard Charts / Workspace JSON are normally synced
by `bench migrate`, but a skipped or half-applied sync leaves the workspace
with blocks that point at records that do not exist (they render as nothing).
This runs after every migrate, creates/updates each record from the app's own
JSON, and logs a clearly named Error Log entry for any record that fails, so
the cause is visible instead of silent.
"""

import json
import os

import frappe

MODULE_DIR = "facilities"
SKIP_KEYS = {"creation", "modified", "modified_by", "owner", "docstatus", "idx"}


def _records(folder):
	path = frappe.get_app_path("facilities_management", MODULE_DIR, folder)
	if not os.path.isdir(path):
		return
	for sub in sorted(os.listdir(path)):
		sub_path = os.path.join(path, sub)
		if not os.path.isdir(sub_path):
			continue
		for fname in os.listdir(sub_path):
			if fname.endswith(".json"):
				with open(os.path.join(sub_path, fname)) as f:
					yield json.load(f)


def _upsert(data):
	doctype, name = data["doctype"], data["name"]
	values = {k: v for k, v in data.items() if k not in SKIP_KEYS}
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
		doc.update(values)
	else:
		doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	if doc.is_new():
		doc.insert()
	else:
		doc.save()


def ensure_dashboard_assets():
	for folder in ("number_card", "dashboard_chart", "dashboard"):
		for data in _records(folder):
			try:
				_upsert(data)
			except Exception:
				frappe.log_error(
					title=f"Facilities: could not set up {data.get('doctype')} '{data.get('name')}'"
				)

	try:
		_sync_workspace()
	except Exception:
		frappe.log_error(title="Facilities: could not update Facilities workspace")

	frappe.db.commit()
	frappe.clear_cache()


def _sync_workspace():
	for data in _records("workspace"):
		if not frappe.db.exists("Workspace", data["name"]):
			continue  # migrate's own sync creates it; nothing to repair
		ws = frappe.get_doc("Workspace", data["name"])
		ws.content = data["content"]
		ws.public = 1
		ws.is_hidden = 0
		ws.set("charts", [])
		for row in data.get("charts", []):
			ws.append("charts", {"chart_name": row["chart_name"], "label": row.get("label")})
		ws.set("number_cards", [])
		for row in data.get("number_cards", []):
			ws.append("number_cards", {"number_card_name": row["number_card_name"], "label": row.get("label")})
		ws.flags.ignore_permissions = True
		ws.flags.ignore_links = True
		ws.save()
