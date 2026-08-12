# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

"""Shared test factories for Event Management."""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import now_datetime


def ensure_roles():
	from event_management.install import _ensure_roles, _ensure_qr_secret

	_ensure_roles()
	_ensure_qr_secret()


def make_event(**overrides):
	ensure_roles()
	now = now_datetime()
	slug = overrides.pop("slug", f"devcon-{frappe.generate_hash(length=6)}")
	doc = frappe.get_doc(
		{
			"doctype": "EM Event",
			"event_name": overrides.pop("event_name", "DevCon"),
			"slug": slug,
			"status": overrides.pop("status", "Registration Open"),
			"event_start": overrides.pop("event_start", now + timedelta(days=7)),
			"event_end": overrides.pop("event_end", now + timedelta(days=7, hours=8)),
			"registration_start": overrides.pop("registration_start", now - timedelta(days=1)),
			"registration_end": overrides.pop("registration_end", now + timedelta(days=6)),
			"currency": overrides.pop("currency", "INR"),
			"allow_cancellation": overrides.pop("allow_cancellation", 1),
			"cancellation_deadline": overrides.pop("cancellation_deadline", now + timedelta(days=5)),
			**overrides,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def make_ticket(event, **overrides):
	doc = frappe.get_doc(
		{
			"doctype": "Event Ticket Type",
			"event": event if isinstance(event, str) else event.name,
			"title": overrides.pop("title", "Regular"),
			"code": overrides.pop("code", "REG"),
			"price": overrides.pop("price", 0),
			"capacity": overrides.pop("capacity", 10),
			"sold_count": overrides.pop("sold_count", 0),
			"reserved_count": overrides.pop("reserved_count", 0),
			"is_active": overrides.pop("is_active", 1),
			**overrides,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def make_addon(event, **overrides):
	doc = frappe.get_doc(
		{
			"doctype": "Event Addon",
			"event": event if isinstance(event, str) else event.name,
			"title": overrides.pop("title", "Lunch"),
			"code": overrides.pop("code", "LUNCH"),
			"price": overrides.pop("price", 0),
			"stock": overrides.pop("stock", 5),
			"sold_count": overrides.pop("sold_count", 0),
			"is_active": overrides.pop("is_active", 1),
			**overrides,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
