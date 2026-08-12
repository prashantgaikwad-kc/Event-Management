"""Concurrency-safe capacity and stock helpers."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

from event_management.utils import AddonUnavailableError, RegistrationClosedError, SoldOutError


OPEN_STATUSES = ("Published", "Registration Open")
BLOCKED_STATUSES = ("Draft", "Registration Closed", "Ongoing", "Completed", "Cancelled")


def validate_event_window(event_name: str):
	event = frappe.db.get_value(
		"EM Event",
		event_name,
		[
			"name",
			"status",
			"event_start",
			"event_end",
			"registration_start",
			"registration_end",
			"allow_cancellation",
			"cancellation_deadline",
			"currency",
		],
		as_dict=True,
	)
	if not event:
		frappe.throw(_("Event not found"))

	if event.status == "Cancelled":
		raise RegistrationClosedError(_("Event is cancelled"))

	if event.status not in OPEN_STATUSES and event.status != "Published":
		# Published may still need Registration Open; allow both Published and Registration Open
		if event.status in ("Registration Closed", "Ongoing", "Completed", "Draft"):
			raise RegistrationClosedError(_("Registration is closed"))

	now = now_datetime()
	if event.registration_start and now < get_datetime(event.registration_start):
		raise RegistrationClosedError(_("Registration has not started"))
	if event.registration_end and now > get_datetime(event.registration_end):
		raise RegistrationClosedError(_("Registration has ended"))

	return event


def lock_ticket_type(ticket_type: str) -> dict:
	rows = frappe.db.sql(
		"""
		SELECT name, event, title, code, price, capacity, sold_count, reserved_count,
		       is_active, sales_start, sales_end
		FROM `tabEvent Ticket Type`
		WHERE name = %s
		FOR UPDATE
		""",
		ticket_type,
		as_dict=True,
	)
	if not rows:
		frappe.throw(_("Ticket type not found"))
	return rows[0]


def lock_addons(addon_ids: list[str]) -> list[dict]:
	if not addon_ids:
		return []
	# Deterministic lock order to reduce deadlock risk
	ordered = sorted({a for a in addon_ids if a})
	placeholders = ", ".join(["%s"] * len(ordered))
	rows = frappe.db.sql(
		f"""
		SELECT name, event, title, code, price, stock, sold_count, is_active, sales_start, sales_end
		FROM `tabEvent Addon`
		WHERE name IN ({placeholders})
		ORDER BY name
		FOR UPDATE
		""",
		tuple(ordered),
		as_dict=True,
	)
	if len(rows) != len(ordered):
		raise AddonUnavailableError(_("One or more add-ons are invalid"))
	return rows


def available_ticket_count(ticket: dict) -> int:
	return cint(ticket.capacity) - cint(ticket.sold_count) - cint(ticket.reserved_count)


def available_addon_stock(addon: dict) -> int:
	return cint(addon.stock) - cint(addon.sold_count)


def validate_ticket_for_purchase(ticket: dict, event_name: str):
	if ticket.event != event_name:
		frappe.throw(_("Ticket type does not belong to this event"))
	if not cint(ticket.is_active):
		raise SoldOutError(_("Selected ticket type is inactive"))

	now = now_datetime()
	if ticket.sales_start and now < get_datetime(ticket.sales_start):
		raise SoldOutError(_("Ticket sales have not started"))
	if ticket.sales_end and now > get_datetime(ticket.sales_end):
		raise SoldOutError(_("Ticket sales have ended"))

	if available_ticket_count(ticket) <= 0:
		raise SoldOutError(_("Ticket type is sold out"))


def validate_addon_for_purchase(addon: dict, event_name: str):
	if addon.event != event_name:
		raise AddonUnavailableError(_("Add-on does not belong to this event"))
	if not cint(addon.is_active):
		raise AddonUnavailableError(_("Add-on is inactive"))

	now = now_datetime()
	if addon.sales_start and now < get_datetime(addon.sales_start):
		raise AddonUnavailableError(_("Add-on sales have not started"))
	if addon.sales_end and now > get_datetime(addon.sales_end):
		raise AddonUnavailableError(_("Add-on sales have ended"))

	if available_addon_stock(addon) <= 0:
		raise AddonUnavailableError(_("Add-on is out of stock"))


def increment_ticket_sold(ticket_name: str, capacity: int) -> None:
	updated = frappe.db.sql(
		"""
		UPDATE `tabEvent Ticket Type`
		SET sold_count = sold_count + 1
		WHERE name = %s AND sold_count + reserved_count < %s
		""",
		(ticket_name, capacity),
	)
	# frappe.db.sql returns rowcount via frappe.db._cursor
	if frappe.db._cursor.rowcount != 1:
		raise SoldOutError(_("Ticket type is sold out"))


def increment_addon_sold(addon_name: str, stock: int) -> None:
	frappe.db.sql(
		"""
		UPDATE `tabEvent Addon`
		SET sold_count = sold_count + 1
		WHERE name = %s AND sold_count < %s
		""",
		(addon_name, stock),
	)
	if frappe.db._cursor.rowcount != 1:
		raise AddonUnavailableError(_("Add-on is out of stock"))


def decrement_ticket_sold(ticket_name: str) -> None:
	frappe.db.sql(
		"""
		UPDATE `tabEvent Ticket Type`
		SET sold_count = GREATEST(sold_count - 1, 0)
		WHERE name = %s
		""",
		ticket_name,
	)


def decrement_addon_sold(addon_name: str) -> None:
	frappe.db.sql(
		"""
		UPDATE `tabEvent Addon`
		SET sold_count = GREATEST(sold_count - 1, 0)
		WHERE name = %s
		""",
		addon_name,
	)


def calculate_totals(ticket_price, addons: list[dict], discount_amount=0, tax_amount=0) -> dict:
	addon_total = sum(flt(a.price) for a in addons)
	subtotal = flt(ticket_price) + flt(addon_total)
	grand_total = subtotal - flt(discount_amount) + flt(tax_amount)
	return {
		"ticket_price": flt(ticket_price),
		"addon_total": flt(addon_total),
		"subtotal": flt(subtotal),
		"discount_amount": flt(discount_amount),
		"tax_amount": flt(tax_amount),
		"grand_total": flt(grand_total),
	}
