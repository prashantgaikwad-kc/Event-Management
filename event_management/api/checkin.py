"""Gate staff check-in APIs."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from event_management.utils import (
	AlreadyCheckedInError,
	CancelledRegistrationError,
	InvalidTokenError,
	NotEligibleError,
	UnpaidRegistrationError,
	fail,
	ok,
)
from event_management.utils.db import atomic
from event_management.utils.permissions import assert_gate_staff
from event_management.utils.token import parse_and_verify_token


def _log_checkin(**kwargs):
	doc = frappe.get_doc({"doctype": "Event Checkin", **kwargs})
	doc.insert(ignore_permissions=True)
	return doc


def _checkin_registration(registration_name: str, source: str = "QR", token_hash: str | None = None):
	"""Core check-in with row lock. Idempotent."""
	rows = frappe.db.sql(
		"""
		SELECT name, event, attendee_name, attendee_email, status, payment_status,
		       checked_in, checked_in_at, checkin_count, ticket_type
		FROM `tabEvent Registration`
		WHERE name = %s
		FOR UPDATE
		""",
		registration_name,
		as_dict=True,
	)
	if not rows:
		raise InvalidTokenError(_("Invalid or expired ticket"))

	reg = rows[0]

	if reg.status == "Cancelled":
		_log_checkin(
			registration=reg.name,
			event=reg.event,
			attendee_name=reg.attendee_name,
			attendee_email=reg.attendee_email,
			result="Cancelled",
			source=source,
			scanned_token_hash=token_hash,
			checked_in_at=now_datetime(),
			checked_in_by=frappe.session.user,
			ip_address=frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None,
		)
		raise CancelledRegistrationError(_("Registration is cancelled"))

	if reg.status != "Confirmed" or reg.payment_status not in ("Paid", "Not Required"):
		_log_checkin(
			registration=reg.name,
			event=reg.event,
			attendee_name=reg.attendee_name,
			attendee_email=reg.attendee_email,
			result="Unpaid",
			source=source,
			scanned_token_hash=token_hash,
			checked_in_at=now_datetime(),
			checked_in_by=frappe.session.user,
		)
		raise UnpaidRegistrationError(_("Registration is unpaid"))

	if cint(reg.checked_in):
		_log_checkin(
			registration=reg.name,
			event=reg.event,
			attendee_name=reg.attendee_name,
			attendee_email=reg.attendee_email,
			result="Already Checked In",
			source=source,
			scanned_token_hash=token_hash,
			checked_in_at=now_datetime(),
			checked_in_by=frappe.session.user,
		)
		raise AlreadyCheckedInError(_("Ticket already checked in"))

	now = now_datetime()
	frappe.db.set_value(
		"Event Registration",
		reg.name,
		{
			"checked_in": 1,
			"checked_in_at": now,
			"checked_in_by": frappe.session.user,
			"checkin_count": 1,
		},
	)

	_log_checkin(
		registration=reg.name,
		event=reg.event,
		attendee_name=reg.attendee_name,
		attendee_email=reg.attendee_email,
		result="Success",
		source=source,
		scanned_token_hash=token_hash,
		checked_in_at=now,
		checked_in_by=frappe.session.user,
		ip_address=getattr(frappe.local, "request_ip", None),
	)

	ticket_title = frappe.db.get_value("Event Ticket Type", reg.ticket_type, "title")
	event_name = frappe.db.get_value("EM Event", reg.event, "event_name")
	return {
		"registration": reg.name,
		"attendee_name": reg.attendee_name,
		"attendee_email": reg.attendee_email,
		"event": reg.event,
		"event_name": event_name,
		"ticket_type": ticket_title,
		"checked_in_at": now,
	}


def _handle_checkin_errors(exc, registration_name=None, payload=None):
	if isinstance(exc, AlreadyCheckedInError):
		reg_id = registration_name or (payload or {}).get("rid")
		checked_in_at = frappe.db.get_value("Event Registration", reg_id, "checked_in_at")
		return fail(str(exc), code="ALREADY_CHECKED_IN", data={"checked_in_at": checked_in_at})
	if isinstance(exc, CancelledRegistrationError):
		return fail(str(exc), code="CANCELLED")
	if isinstance(exc, UnpaidRegistrationError):
		return fail(str(exc), code="UNPAID")
	if isinstance(exc, NotEligibleError):
		return fail(str(exc), code="NOT_ELIGIBLE")
	if isinstance(exc, InvalidTokenError):
		return fail(str(exc), code="INVALID_TOKEN")
	raise exc


@frappe.whitelist()
def checkin_by_qr(token: str):
	assert_gate_staff()
	payload = {}
	try:
		payload = parse_and_verify_token(token)
	except InvalidTokenError as exc:
		return fail(str(exc), code="INVALID_TOKEN")

	try:
		with atomic("checkin_qr"):
			reg_name = payload["rid"]
			token_hash = payload["_token_hash"]

			stored_hash = frappe.db.get_value("Event Registration", reg_name, "qr_token_hash")
			if not stored_hash or stored_hash != token_hash:
				raise InvalidTokenError(_("Invalid or expired ticket"))

			data = _checkin_registration(reg_name, source="QR", token_hash=token_hash)
			return ok(data, code="VALID", message=_("Checked in"))
	except (
		AlreadyCheckedInError,
		CancelledRegistrationError,
		UnpaidRegistrationError,
		NotEligibleError,
		InvalidTokenError,
	) as exc:
		return _handle_checkin_errors(exc, payload=payload)
	except Exception:
		frappe.log_error(title="checkin_by_qr failed")
		return fail(_("Check-in failed"), code="ERROR")


@frappe.whitelist()
def search_registration(query: str, event: str | None = None):
	assert_gate_staff()
	query = (query or "").strip()
	if len(query) < 2:
		return ok([])

	filters = {}
	if event:
		filters["event"] = event

	or_filters = [
		["attendee_name", "like", f"%{query}%"],
		["attendee_email", "like", f"%{query}%"],
		["registration_reference", "like", f"%{query}%"],
		["name", "like", f"%{query}%"],
	]

	rows = frappe.get_all(
		"Event Registration",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"registration_reference",
			"attendee_name",
			"attendee_email",
			"event",
			"ticket_type",
			"payment_status",
			"status",
			"checked_in",
			"checked_in_at",
		],
		limit_page_length=20,
	)
	for row in rows:
		row["event_name"] = frappe.db.get_value("EM Event", row.event, "event_name")
		row["ticket_title"] = frappe.db.get_value("Event Ticket Type", row.ticket_type, "title")
	return ok(rows)


@frappe.whitelist()
def checkin_by_registration(registration: str):
	assert_gate_staff()
	try:
		with atomic("checkin_manual"):
			data = _checkin_registration(registration, source="Manual")
			return ok(data, code="VALID", message=_("Checked in"))
	except (
		AlreadyCheckedInError,
		CancelledRegistrationError,
		UnpaidRegistrationError,
		InvalidTokenError,
	) as exc:
		return _handle_checkin_errors(exc, registration_name=registration)
	except Exception:
		frappe.log_error(title="checkin_by_registration failed")
		return fail(_("Check-in failed"), code="ERROR")
