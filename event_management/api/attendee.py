"""Attendee-facing APIs."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from event_management.utils import fail, ok, require_login
from event_management.utils.db import atomic
from event_management.utils.capacity import (
	calculate_totals,
	increment_addon_sold,
	increment_ticket_sold,
	lock_addons,
	lock_ticket_type,
	validate_addon_for_purchase,
	validate_event_window,
	validate_ticket_for_purchase,
	available_ticket_count,
	available_addon_stock,
	decrement_addon_sold,
	decrement_ticket_sold,
)
from event_management.utils.payments import create_payment_order
from event_management.utils.ticket import assign_qr_token, generate_qr_png_base64


def _parse_addon_ids(addon_ids):
	if not addon_ids:
		return []
	if isinstance(addon_ids, str):
		addon_ids = addon_ids.strip()
		if not addon_ids:
			return []
		try:
			addon_ids = json.loads(addon_ids)
		except json.JSONDecodeError:
			addon_ids = [a.strip() for a in addon_ids.split(",") if a.strip()]
	return list(addon_ids)


@frappe.whitelist(allow_guest=True)
def list_upcoming_events(limit: int = 20):
	limit = min(int(limit or 20), 100)
	events = frappe.get_all(
		"EM Event",
		filters={
			"status": ("in", ["Published", "Registration Open"]),
			"event_start": (">=", now_datetime()),
		},
		fields=[
			"name",
			"event_name",
			"slug",
			"short_description",
			"cover_image",
			"venue_name",
			"city",
			"event_start",
			"event_end",
			"status",
			"is_featured",
		],
		order_by="event_start asc",
		limit_page_length=limit,
	)
	return ok(events)


@frappe.whitelist(allow_guest=True)
def get_event(event: str | None = None, slug: str | None = None):
	filters = {}
	if event:
		filters["name"] = event
	elif slug:
		filters["slug"] = slug
	else:
		frappe.throw(_("event or slug is required"))

	name = frappe.db.get_value("EM Event", filters, "name")
	if not name:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("EM Event", name)
	# Only expose published-ish events to guests
	if frappe.session.user == "Guest" and doc.status in ("Draft", "Cancelled"):
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	tickets = frappe.get_all(
		"Event Ticket Type",
		filters={"event": name, "is_active": 1},
		fields=["name", "title", "code", "description", "price", "capacity", "sold_count", "reserved_count", "sort_order"],
		order_by="sort_order asc",
	)
	for t in tickets:
		avail = available_ticket_count(t)
		t["available"] = avail > 0
		t["available_count"] = avail
		# Do not expose raw sold counters unnecessarily beyond availability
		t.pop("sold_count", None)
		t.pop("reserved_count", None)

	addons = frappe.get_all(
		"Event Addon",
		filters={"event": name, "is_active": 1},
		fields=["name", "title", "code", "description", "price", "stock", "sold_count"],
	)
	for a in addons:
		stock_left = available_addon_stock(a)
		a["available"] = stock_left > 0
		a["available_stock"] = stock_left
		a.pop("sold_count", None)

	data = {
		"name": doc.name,
		"event_name": doc.event_name,
		"slug": doc.slug,
		"description": doc.description,
		"short_description": doc.short_description,
		"cover_image": doc.cover_image,
		"venue_name": doc.venue_name,
		"venue_address": doc.venue_address,
		"city": doc.city,
		"event_start": doc.event_start,
		"event_end": doc.event_end,
		"registration_start": doc.registration_start,
		"registration_end": doc.registration_end,
		"status": doc.status,
		"currency": doc.currency,
		"allow_cancellation": doc.allow_cancellation,
		"cancellation_deadline": doc.cancellation_deadline,
		"terms_and_conditions": doc.terms_and_conditions,
		"ticket_types": tickets,
		"addons": addons,
	}
	return ok(data)


@frappe.whitelist(allow_guest=True)
def get_event_availability(event: str):
	tickets = frappe.get_all(
		"Event Ticket Type",
		filters={"event": event, "is_active": 1},
		fields=["name", "code", "capacity", "sold_count", "reserved_count"],
	)
	addons = frappe.get_all(
		"Event Addon",
		filters={"event": event, "is_active": 1},
		fields=["name", "code", "stock", "sold_count"],
	)
	return ok(
		{
			"tickets": [
				{"name": t.name, "code": t.code, "available_count": available_ticket_count(t)}
				for t in tickets
			],
			"addons": [
				{"name": a.name, "code": a.code, "available_stock": available_addon_stock(a)}
				for a in addons
			],
		}
	)


@frappe.whitelist()
def create_registration(event: str, ticket_type: str, addon_ids=None, attendee_name=None, attendee_email=None, attendee_phone=None):
	require_login()
	addon_ids = _parse_addon_ids(addon_ids)

	user = frappe.session.user
	attendee_name = attendee_name or frappe.db.get_value("User", user, "full_name") or user
	attendee_email = attendee_email or frappe.db.get_value("User", user, "email") or user

	qr_preview = False
	token = None
	payment_info = None

	with atomic("create_registration"):
		event_doc = validate_event_window(event)
		ticket = lock_ticket_type(ticket_type)
		validate_ticket_for_purchase(ticket, event)

		addons = lock_addons(addon_ids)
		for addon in addons:
			validate_addon_for_purchase(addon, event)

		totals = calculate_totals(ticket.price, addons)

		reg = frappe.get_doc(
			{
				"doctype": "Event Registration",
				"event": event,
				"attendee_user": user,
				"attendee_name": attendee_name,
				"attendee_email": attendee_email,
				"attendee_phone": attendee_phone,
				"ticket_type": ticket.name,
				"ticket_price": totals["ticket_price"],
				"addon_total": totals["addon_total"],
				"subtotal": totals["subtotal"],
				"discount_amount": totals["discount_amount"],
				"tax_amount": totals["tax_amount"],
				"grand_total": totals["grand_total"],
				"status": "Pending Payment",
				"payment_status": "Pending" if totals["grand_total"] > 0 else "Not Required",
				"items": [
					{
						"addon": a.name,
						"addon_code": a.code,
						"qty": 1,
						"unit_price": a.price,
						"amount": a.price,
					}
					for a in addons
				],
			}
		)
		reg.insert(ignore_permissions=True)

		increment_ticket_sold(ticket.name, ticket.capacity)
		for addon in addons:
			increment_addon_sold(addon.name, addon.stock)

		if totals["grand_total"] <= 0:
			reg.db_set({"status": "Confirmed", "payment_status": "Not Required", "paid_at": now_datetime()})
			token = assign_qr_token(reg)
			payment_info = {"required": False}
			qr_preview = True
		else:
			payment_info = create_payment_order(reg.name)

	data = {
		"registration": reg.name,
		"registration_reference": reg.registration_reference,
		"status": frappe.db.get_value("Event Registration", reg.name, "status"),
		"payment_status": frappe.db.get_value("Event Registration", reg.name, "payment_status"),
		"grand_total": totals["grand_total"],
		"currency": event_doc.currency,
		"payment": payment_info,
	}
	if qr_preview and token:
		data["has_ticket"] = True
	return ok(data, message=_("Registration created"))


@frappe.whitelist()
def list_my_registrations():
	require_login()
	rows = frappe.get_all(
		"Event Registration",
		filters={"attendee_user": frappe.session.user},
		fields=[
			"name",
			"registration_reference",
			"event",
			"ticket_type",
			"status",
			"payment_status",
			"grand_total",
			"registration_time",
			"checked_in",
			"checked_in_at",
		],
		order_by="registration_time desc",
	)
	for row in rows:
		row["event_name"] = frappe.db.get_value("EM Event", row.event, "event_name")
		row["ticket_title"] = frappe.db.get_value("Event Ticket Type", row.ticket_type, "title")
	return ok(rows)


@frappe.whitelist()
def get_my_registration(registration: str):
	require_login()
	reg = frappe.get_doc("Event Registration", registration)
	if reg.attendee_user != frappe.session.user and not frappe.has_permission(
		"Event Registration", "read", reg
	):
		# Organizers may read; attendees only own
		from event_management.utils.permissions import is_organizer

		if not is_organizer() and reg.attendee_user != frappe.session.user:
			frappe.throw(_("Not permitted"), frappe.PermissionError)

	if reg.attendee_user != frappe.session.user:
		from event_management.utils.permissions import is_organizer, is_gate_staff

		if not (is_organizer() or is_gate_staff()):
			frappe.throw(_("Not permitted"), frappe.PermissionError)

	event = frappe.get_doc("EM Event", reg.event)
	items = [
		{
			"addon": i.addon,
			"addon_code": i.addon_code,
			"qty": i.qty,
			"unit_price": i.unit_price,
			"amount": i.amount,
			"title": frappe.db.get_value("Event Addon", i.addon, "title"),
		}
		for i in reg.items
	]
	return ok(
		{
			"name": reg.name,
			"registration_reference": reg.registration_reference,
			"status": reg.status,
			"payment_status": reg.payment_status,
			"ticket_type": reg.ticket_type,
			"ticket_title": frappe.db.get_value("Event Ticket Type", reg.ticket_type, "title"),
			"ticket_price": reg.ticket_price,
			"addon_total": reg.addon_total,
			"grand_total": reg.grand_total,
			"registration_time": reg.registration_time,
			"checked_in": reg.checked_in,
			"checked_in_at": reg.checked_in_at,
			"items": items,
			"event": {
				"name": event.name,
				"event_name": event.event_name,
				"slug": event.slug,
				"event_start": event.event_start,
				"event_end": event.event_end,
				"venue_name": event.venue_name,
				"allow_cancellation": event.allow_cancellation,
				"cancellation_deadline": event.cancellation_deadline,
			},
		}
	)


@frappe.whitelist()
def get_my_ticket(registration: str):
	require_login()
	reg = frappe.get_doc("Event Registration", registration)
	if reg.attendee_user != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if reg.status != "Confirmed":
		return fail(_("Ticket is not available"), code="NOT_ELIGIBLE")

	token = assign_qr_token(reg)
	event = frappe.get_doc("EM Event", reg.event)
	return ok(
		{
			"registration": reg.name,
			"registration_reference": reg.registration_reference,
			"attendee_name": reg.attendee_name,
			"event_name": event.event_name,
			"event_start": event.event_start,
			"event_end": event.event_end,
			"venue_name": event.venue_name,
			"ticket_title": frappe.db.get_value("Event Ticket Type", reg.ticket_type, "title"),
			"addons": [frappe.db.get_value("Event Addon", i.addon, "title") for i in reg.items],
			"qr_token": token,
			"qr_image_base64": generate_qr_png_base64(token),
			"pdf_url": f"/api/method/event_management.api.attendee.download_my_ticket_pdf?registration={registration}",
		}
	)


@frappe.whitelist()
def download_my_ticket_pdf(registration: str):
	require_login()
	reg = frappe.get_doc("Event Registration", registration)
	if reg.attendee_user != frappe.session.user:
		from event_management.utils.permissions import is_organizer

		if not is_organizer():
			frappe.throw(_("Not permitted"), frappe.PermissionError)
	if reg.status != "Confirmed":
		frappe.throw(_("Ticket is not available"))

	from frappe.utils.print_format import download_pdf

	return download_pdf("Event Registration", registration, "Event Ticket", no_letterhead=1)


@frappe.whitelist()
def cancel_registration(registration: str):
	require_login()
	from frappe.utils import get_datetime

	with atomic("cancel_registration"):
		rows = frappe.db.sql(
			"""
			SELECT name, event, ticket_type, status, attendee_user, payment_status
			FROM `tabEvent Registration`
			WHERE name = %s
			FOR UPDATE
			""",
			registration,
			as_dict=True,
		)
		if not rows:
			frappe.throw(_("Registration not found"))
		reg = rows[0]

		if reg.attendee_user != frappe.session.user:
			from event_management.utils.permissions import is_organizer

			if not is_organizer():
				frappe.throw(_("Not permitted"), frappe.PermissionError)

		if reg.status != "Confirmed":
			frappe.throw(_("Only confirmed registrations can be cancelled"))

		event = frappe.db.get_value(
			"EM Event",
			reg.event,
			["allow_cancellation", "cancellation_deadline"],
			as_dict=True,
		)
		if not event.allow_cancellation:
			frappe.throw(_("Cancellation is not allowed for this event"))
		if event.cancellation_deadline and now_datetime() > get_datetime(event.cancellation_deadline):
			frappe.throw(_("Cancellation deadline has passed"))

		ticket = lock_ticket_type(reg.ticket_type)
		item_addons = frappe.get_all(
			"Event Registration Item",
			filters={"parent": registration},
			pluck="addon",
		)
		addons = lock_addons(item_addons)

		decrement_ticket_sold(ticket.name)
		for addon in addons:
			decrement_addon_sold(addon.name)

		frappe.db.set_value(
			"Event Registration",
			registration,
			{
				"status": "Cancelled",
				"cancelled_at": now_datetime(),
			},
		)

		if reg.payment_status == "Paid":
			from event_management.utils.payments import refund_payment

			refund_payment(registration)

	return ok({"registration": registration, "status": "Cancelled"}, message=_("Registration cancelled"))
