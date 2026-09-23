# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100},
		{"label": _("Created"), "fieldname": "total_created", "fieldtype": "Int", "width": 90},
		{"label": _("Completed/Closed"), "fieldname": "completed", "fieldtype": "Int", "width": 130},
		{"label": _("Cancelled/Rejected"), "fieldname": "cancelled", "fieldtype": "Int", "width": 130},
		{"label": _("Critical"), "fieldname": "critical_count", "fieldtype": "Int", "width": 90},
		{"label": _("High"), "fieldname": "high_count", "fieldtype": "Int", "width": 90},
		{"label": _("Avg Turnaround (hrs)"), "fieldname": "avg_turnaround", "fieldtype": "Float", "width": 150},
	]


def get_data(filters):
	conditions = ""
	values = {}
	if filters.get("department"):
		conditions += " and department = %(department)s"
		values["department"] = filters["department"]
	if filters.get("year"):
		conditions += " and YEAR(creation) = %(year)s"
		values["year"] = filters["year"]

	created_rows = frappe.db.sql(
		f"""
		select
			DATE_FORMAT(creation, '%%Y-%%m') as month,
			count(*) as total_created,
			sum(case when status in ('Completed', 'Closed') then 1 else 0 end) as completed,
			sum(case when status in ('Cancelled', 'Rejected') then 1 else 0 end) as cancelled,
			sum(case when priority = 'Critical' then 1 else 0 end) as critical_count,
			sum(case when priority = 'High' then 1 else 0 end) as high_count
		from `tabFacilities Work Order`
		where 1=1 {conditions}
		group by month
		order by month desc
		""",
		values,
		as_dict=True,
	)

	turnaround_rows = frappe.db.sql(
		"""
		select
			DATE_FORMAT(completed_on, '%%Y-%%m') as month,
			avg(TIMESTAMPDIFF(HOUR, started_on, completed_on)) as avg_turnaround
		from `tabFacilities Work Order`
		where completed_on is not null and started_on is not null
		group by month
		""",
		as_dict=True,
	)
	turnaround_by_month = {r.month: r.avg_turnaround for r in turnaround_rows}

	for r in created_rows:
		avg_val = turnaround_by_month.get(r.month)
		r["avg_turnaround"] = round(avg_val, 1) if avg_val is not None else None

	return created_rows


def get_chart(data):
	if not data:
		return None
	months = [r["month"] for r in reversed(data)]
	created = [r["total_created"] for r in reversed(data)]
	completed = [r["completed"] for r in reversed(data)]
	return {
		"data": {
			"labels": months,
			"datasets": [
				{"name": _("Created"), "values": created},
				{"name": _("Completed"), "values": completed},
			],
		},
		"type": "line",
	}
