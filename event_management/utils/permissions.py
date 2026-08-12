"""Permission helpers for Event Management."""

from __future__ import annotations

import frappe

from event_management.utils import user_has_role


ORGANIZER_ROLES = ("Event Organizer", "System Manager", "Administrator")
GATE_ROLES = ("Event Gate Staff", "Event Organizer", "System Manager", "Administrator")


def is_organizer(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)).intersection({"Event Organizer", "System Manager"}))


def is_gate_staff(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(
		set(frappe.get_roles(user)).intersection(
			{"Event Gate Staff", "Event Organizer", "System Manager"}
		)
	)


def registration_query(user: str) -> str:
	"""Restrict Event Registration list for attendees to their own rows."""
	if not user or user == "Administrator":
		return ""
	roles = set(frappe.get_roles(user))
	if roles.intersection({"System Manager", "Event Organizer", "Event Gate Staff"}):
		return ""
	return f"`tabEvent Registration`.attendee_user = {frappe.db.escape(user)}"


def registration_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator" or is_organizer(user) or is_gate_staff(user):
		return True
	if getattr(doc, "attendee_user", None) == user:
		return True
	return False


def assert_organizer():
	if not is_organizer():
		frappe.throw("Not permitted", frappe.PermissionError)


def assert_gate_staff():
	if not is_gate_staff():
		frappe.throw("Not permitted", frappe.PermissionError)
