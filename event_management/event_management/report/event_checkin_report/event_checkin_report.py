# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = None
	confirmed = sum(1 for r in data if r.get("status") == "Confirmed")
	checked = sum(1 for r in data if r.get("checked_in") and r.get("status") == "Confirmed")
	pct = (checked / confirmed * 100.0) if confirmed else 0.0
	report_summary = [
		{"value": confirmed, "label": _("Total Confirmed"), "datatype": "Int"},
		{"value": checked, "label": _("Checked In"), "datatype": "Int"},
		{"value": max(confirmed - checked, 0), "label": _("Not Checked In"), "datatype": "Int"},
		{"value": round(pct, 2), "label": _("Attendance %"), "datatype": "Float"},
	]
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{"label": _("Registration"), "fieldname": "name", "fieldtype": "Link", "options": "Event Registration", "width": 140},
		{"label": _("Attendee Name"), "fieldname": "attendee_name", "fieldtype": "Data", "width": 160},
		{"label": _("Email"), "fieldname": "attendee_email", "fieldtype": "Data", "width": 180},
		{"label": _("Phone"), "fieldname": "attendee_phone", "fieldtype": "Data", "width": 120},
		{"label": _("Event"), "fieldname": "event", "fieldtype": "Link", "options": "EM Event", "width": 140},
		{"label": _("Ticket Type"), "fieldname": "ticket_title", "fieldtype": "Data", "width": 120},
		{"label": _("Add-ons"), "fieldname": "addons", "fieldtype": "Data", "width": 160},
		{"label": _("Payment Status"), "fieldname": "payment_status", "fieldtype": "Data", "width": 110},
		{"label": _("Check-in Status"), "fieldname": "checkin_status", "fieldtype": "Data", "width": 120},
		{"label": _("Checked-in At"), "fieldname": "checked_in_at", "fieldtype": "Datetime", "width": 160},
		{"label": _("Checked-in By"), "fieldname": "checked_in_by", "fieldtype": "Link", "options": "User", "width": 140},
	]


def get_data(filters):
	conds = {}
	if filters.get("event"):
		conds["event"] = filters["event"]
	rows = frappe.get_all(
		"Event Registration",
		filters=conds,
		fields=[
			"name",
			"attendee_name",
			"attendee_email",
			"attendee_phone",
			"event",
			"ticket_type",
			"payment_status",
			"status",
			"checked_in",
			"checked_in_at",
			"checked_in_by",
		],
		order_by="registration_time desc",
	)
	for row in rows:
		row["ticket_title"] = frappe.db.get_value("Event Ticket Type", row.ticket_type, "title")
		addons = frappe.get_all("Event Registration Item", filters={"parent": row.name}, fields=["addon"])
		row["addons"] = ", ".join(
			frappe.db.get_value("Event Addon", a.addon, "title") or "" for a in addons
		)
		row["checkin_status"] = "Checked In" if cint(row.checked_in) else "Not Checked In"
	return rows
