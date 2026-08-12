"""Organizer dashboard / report / export APIs."""

from __future__ import annotations

import csv
import io
import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from event_management.utils import ok
from event_management.utils.permissions import assert_organizer


def _parse_filters(filters):
	if not filters:
		return {}
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except json.JSONDecodeError:
			filters = {}
	return filters or {}


@frappe.whitelist()
def dashboard_metrics(event: str | None = None, from_date: str | None = None, to_date: str | None = None):
	assert_organizer()

	conditions = ["1=1"]
	values = {}
	if event:
		conditions.append("event = %(event)s")
		values["event"] = event
	if from_date:
		conditions.append("registration_time >= %(from_date)s")
		values["from_date"] = from_date
	if to_date:
		conditions.append("registration_time <= %(to_date)s")
		values["to_date"] = to_date

	where = " AND ".join(conditions)

	stats = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS total_registrations,
			SUM(CASE WHEN status = 'Confirmed' THEN 1 ELSE 0 END) AS confirmed_registrations,
			SUM(CASE WHEN payment_status = 'Paid' THEN 1 ELSE 0 END) AS paid_registrations,
			SUM(CASE WHEN payment_status = 'Paid' THEN grand_total ELSE 0 END) AS revenue,
			SUM(CASE WHEN checked_in = 1 AND status = 'Confirmed' THEN 1 ELSE 0 END) AS checked_in
		FROM `tabEvent Registration`
		WHERE {where}
		""",
		values,
		as_dict=True,
	)[0]

	confirmed = cint(stats.confirmed_registrations)
	checked_in = cint(stats.checked_in)
	attendance_pct = (checked_in / confirmed * 100.0) if confirmed else 0.0

	capacity_remaining = None
	if event:
		cap = frappe.db.sql(
			"""
			SELECT
				COALESCE(SUM(capacity), 0) AS capacity,
				COALESCE(SUM(sold_count), 0) AS sold
			FROM `tabEvent Ticket Type`
			WHERE event = %s
			""",
			event,
			as_dict=True,
		)[0]
		capacity_remaining = cint(cap.capacity) - cint(cap.sold)

	# Trends
	reg_trend = frappe.db.sql(
		f"""
		SELECT DATE(registration_time) AS day, COUNT(*) AS count
		FROM `tabEvent Registration`
		WHERE {where}
		GROUP BY DATE(registration_time)
		ORDER BY day
		""",
		values,
		as_dict=True,
	)
	rev_trend = frappe.db.sql(
		f"""
		SELECT DATE(paid_at) AS day, SUM(grand_total) AS revenue
		FROM `tabEvent Registration`
		WHERE {where} AND payment_status = 'Paid' AND paid_at IS NOT NULL
		GROUP BY DATE(paid_at)
		ORDER BY day
		""",
		values,
		as_dict=True,
	)

	ticket_dist_filters = {"status": "Confirmed"}
	if event:
		ticket_dist_filters["event"] = event
	ticket_dist = frappe.db.sql(
		"""
		SELECT t.title AS ticket_type, COUNT(*) AS count
		FROM `tabEvent Registration` r
		INNER JOIN `tabEvent Ticket Type` t ON t.name = r.ticket_type
		WHERE r.status = 'Confirmed' {event_clause}
		GROUP BY t.title
		ORDER BY count DESC
		""".format(event_clause="AND r.event = %(event)s" if event else ""),
		{"event": event} if event else {},
		as_dict=True,
	)

	return ok(
		{
			"kpis": {
				"total_registrations": cint(stats.total_registrations),
				"confirmed_registrations": confirmed,
				"paid_registrations": cint(stats.paid_registrations),
				"revenue": flt(stats.revenue),
				"checked_in": checked_in,
				"attendance_percentage": round(attendance_pct, 2),
				"capacity_remaining": capacity_remaining,
			},
			"charts": {
				"registration_trend": reg_trend,
				"revenue_trend": rev_trend,
				"ticket_type_distribution": ticket_dist,
				"attendance": [
					{"label": "Checked In", "count": checked_in},
					{"label": "Not Checked In", "count": max(confirmed - checked_in, 0)},
				],
			},
		}
	)


@frappe.whitelist()
def registration_report(event: str | None = None, filters=None):
	assert_organizer()
	filters = _parse_filters(filters)
	conds = {}
	if event:
		conds["event"] = event
	if filters.get("ticket_type"):
		conds["ticket_type"] = filters["ticket_type"]
	if filters.get("payment_status"):
		conds["payment_status"] = filters["payment_status"]
	if filters.get("checked_in") is not None:
		conds["checked_in"] = cint(filters["checked_in"])

	rows = frappe.get_all(
		"Event Registration",
		filters=conds,
		fields=[
			"name",
			"registration_reference",
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
			"grand_total",
			"registration_time",
		],
		order_by="registration_time desc",
		limit_page_length=1000,
	)

	for row in rows:
		row["event_name"] = frappe.db.get_value("EM Event", row.event, "event_name")
		row["ticket_title"] = frappe.db.get_value("Event Ticket Type", row.ticket_type, "title")
		addons = frappe.get_all(
			"Event Registration Item",
			filters={"parent": row.name},
			fields=["addon"],
		)
		row["addons"] = ", ".join(
			frappe.db.get_value("Event Addon", a.addon, "title") or a.addon for a in addons
		)

	confirmed = sum(1 for r in rows if r.status == "Confirmed")
	checked = sum(1 for r in rows if r.checked_in and r.status == "Confirmed")
	attendance_pct = (checked / confirmed * 100.0) if confirmed else 0.0

	return ok(
		{
			"rows": rows,
			"summary": {
				"total_confirmed": confirmed,
				"checked_in": checked,
				"not_checked_in": max(confirmed - checked, 0),
				"attendance_percentage": round(attendance_pct, 2),
			},
		}
	)


@frappe.whitelist()
def export_attendees(event: str | None = None, filters=None):
	assert_organizer()
	report = registration_report(event=event, filters=filters)
	rows = report["data"]["rows"]

	output = io.StringIO()
	writer = csv.writer(output)
	writer.writerow(
		[
			"Registration Reference",
			"Attendee Name",
			"Email",
			"Phone",
			"Event",
			"Ticket Type",
			"Add-ons",
			"Ticket Price",
			"Addon Total",
			"Grand Total",
			"Payment Status",
			"Registered At",
			"Check-in Status",
			"Checked-in At",
		]
	)
	for r in rows:
		full = frappe.db.get_value(
			"Event Registration",
			r["name"],
			["ticket_price", "addon_total", "grand_total"],
			as_dict=True,
		)
		writer.writerow(
			[
				r.get("registration_reference"),
				r.get("attendee_name"),
				r.get("attendee_email"),
				r.get("attendee_phone"),
				r.get("event_name"),
				r.get("ticket_title"),
				r.get("addons"),
				full.ticket_price,
				full.addon_total,
				full.grand_total,
				r.get("payment_status"),
				r.get("registration_time"),
				"Checked In" if r.get("checked_in") else "Not Checked In",
				r.get("checked_in_at"),
			]
		)

	content = output.getvalue()
	frappe.response["type"] = "csv"
	frappe.response["doctype"] = f"attendees-{event or 'all'}"
	frappe.response["result"] = cstr(content)
