# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

"""Shared helpers for the Facilities script reports."""

from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, getdate, today

WO = "Facilities Work Order"
OPEN_STATUSES = ["Draft", "Submitted", "Pending Approval", "Approved", "Assigned", "In Progress", "On Hold"]
DONE_STATUSES = ["Completed", "Closed"]
SLA_STATUSES = ["Submitted", "Pending Approval", "Approved", "Assigned", "In Progress", "On Hold", "Completed", "Closed"]


def date_range(filters, default_days=180):
	"""(from_date, to_date) as dates, validated and defaulted."""
	to_date = getdate(filters.get("to_date") or today())
	from_date = getdate(filters.get("from_date") or add_days(to_date, -default_days))
	if from_date > to_date:
		frappe.throw(frappe._("From Date cannot be after To Date"))
	return from_date, to_date


def end_of_day(d):
	return get_datetime(f"{d} 23:59:59")


def start_of_day(d):
	return get_datetime(f"{d} 00:00:00")


def hours_between(start, end):
	if not start or not end:
		return None
	return round((get_datetime(end) - get_datetime(start)).total_seconds() / 3600, 1)


def avg(values):
	values = [v for v in values if v is not None]
	return round(sum(values) / len(values), 1) if values else None


def median(values):
	values = sorted(v for v in values if v is not None)
	if not values:
		return None
	mid = len(values) // 2
	return round(values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2, 1)


def pct(part, whole):
	return round(part * 100.0 / whole, 1) if whole else None


def stars(rating):
	"""Rating fields are stored 0-1; show them on the familiar 1-5 scale."""
	return round(rating * 5, 2) if rating else None


def months_between(from_date, to_date):
	"""Ordered list of 'YYYY-MM' keys covering the range (capped at 60)."""
	keys, cur = [], from_date.replace(day=1)
	while cur <= to_date and len(keys) < 60:
		keys.append(cur.strftime("%Y-%m"))
		cur = (cur + timedelta(days=32)).replace(day=1)
	return keys


def wo_filters(filters, **extra):
	"""Common Work Order filters shared by many reports."""
	out = {}
	for key in ("department", "priority", "assigned_to", "work_order_type", "source", "client_type"):
		if filters.get(key):
			out[key] = filters[key]
	out.update(extra)
	return out


def summary_card(label, value, datatype="Int", indicator=None):
	card = {"label": label, "value": value if value is not None else 0, "datatype": datatype}
	if indicator:
		card["indicator"] = indicator
	return card
