"""Shared exceptions and response helpers."""

from __future__ import annotations

import frappe
from frappe import _


class EventManagementError(frappe.ValidationError):
	code = "ERROR"

	def __init__(self, message: str | None = None, code: str | None = None):
		self.code = code or self.code
		super().__init__(message or self.code)


class RegistrationClosedError(EventManagementError):
	code = "REGISTRATION_CLOSED"


class SoldOutError(EventManagementError):
	code = "SOLD_OUT"


class AddonUnavailableError(EventManagementError):
	code = "ADDON_UNAVAILABLE"


class InvalidTokenError(EventManagementError):
	code = "INVALID_TOKEN"


class AlreadyCheckedInError(EventManagementError):
	code = "ALREADY_CHECKED_IN"


class UnpaidRegistrationError(EventManagementError):
	code = "UNPAID"


class CancelledRegistrationError(EventManagementError):
	code = "CANCELLED"


class NotEligibleError(EventManagementError):
	code = "NOT_ELIGIBLE"


class PermissionDeniedError(EventManagementError):
	code = "PERMISSION_DENIED"


def ok(data=None, message: str | None = None, code: str | None = None):
	payload = {"ok": True, "data": data or {}}
	if message:
		payload["message"] = message
	if code:
		payload["code"] = code
	return payload


def fail(message: str, code: str = "ERROR", data=None):
	payload = {"ok": False, "code": code, "message": message}
	if data is not None:
		payload["data"] = data
	return payload


def require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)


def user_has_role(*roles: str) -> bool:
	if frappe.session.user == "Administrator":
		return True
	user_roles = set(frappe.get_roles(frappe.session.user))
	return bool(user_roles.intersection(roles))


def require_roles(*roles: str):
	if not user_has_role(*roles):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
