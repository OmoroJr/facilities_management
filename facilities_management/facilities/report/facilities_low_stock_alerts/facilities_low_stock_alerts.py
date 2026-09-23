# Copyright (c) 2026, PingTap Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link",
		 "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link",
		 "options": "Item Group", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link",
		 "options": "Warehouse", "width": 150},
		{"label": _("Actual Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float", "width": 110},
		{"label": _("Shortfall"), "fieldname": "shortfall", "fieldtype": "Float", "width": 100},
		{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float", "width": 110},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
	]


def get_data(filters):
	conditions = "item.disabled = 0 and item.is_stock_item = 1 and ir.reorder_level > 0"
	values = {}
	if filters.get("item_group"):
		conditions += " and item.item_group = %(item_group)s"
		values["item_group"] = filters["item_group"]
	if filters.get("warehouse"):
		conditions += " and ir.warehouse = %(warehouse)s"
		values["warehouse"] = filters["warehouse"]

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			item.stock_uom,
			ir.warehouse,
			ir.reorder_level,
			ir.reorder_qty,
			coalesce(bin.actual_qty, 0) as actual_qty
		from `tabItem Reorder` ir
		inner join `tabItem` item on item.name = ir.parent
		left join `tabBin` bin on bin.item_code = item.name and bin.warehouse = ir.warehouse
		where {conditions}
			and coalesce(bin.actual_qty, 0) < ir.reorder_level
		order by item.item_group asc, item.item_code asc
		""",
		values,
		as_dict=True,
	)
	for r in rows:
		r["shortfall"] = (r.reorder_level or 0) - (r.actual_qty or 0)
	return rows
