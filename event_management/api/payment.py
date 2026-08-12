"""Payment APIs."""

from __future__ import annotations

import json

import frappe
from frappe import _

from event_management.utils import ok, require_login
from event_management.utils.payments import create_payment_order as _create_order
from event_management.utils.payments import verify_payment as _verify


@frappe.whitelist()
def create_payment_order(registration: str):
	require_login()
	reg = frappe.get_doc("Event Registration", registration)
	if reg.attendee_user != frappe.session.user:
		from event_management.utils.permissions import is_organizer

		if not is_organizer():
			frappe.throw(_("Not permitted"), frappe.PermissionError)
	return ok(_create_order(registration))


@frappe.whitelist()
def verify_payment(registration: str, payload=None):
	require_login()
	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except json.JSONDecodeError:
			payload = {}
	reg = frappe.get_doc("Event Registration", registration)
	if reg.attendee_user != frappe.session.user:
		from event_management.utils.permissions import is_organizer

		if not is_organizer():
			frappe.throw(_("Not permitted"), frappe.PermissionError)
	return ok(_verify(registration, payload or {}))


@frappe.whitelist(allow_guest=True)
def payment_webhook():
	"""Idempotent webhook endpoint — verify gateway signature before applying."""
	payload = frappe.request.get_data(as_text=True) if frappe.request else "{}"
	try:
		data = json.loads(payload or "{}")
	except json.JSONDecodeError:
		return ok({"processed": False, "reason": "invalid json"})

	# Expected shape depends on Razorpay; keep processing idempotent
	registration = data.get("registration") or data.get("notes", {}).get("registration")
	payment_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("id") or data.get(
		"razorpay_payment_id"
	)
	order_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id") or data.get(
		"razorpay_order_id"
	)

	if not registration:
		# Try resolve by order id
		if order_id:
			registration = frappe.db.get_value("Event Registration", {"payment_reference": order_id}, "name")

	if not registration:
		return ok({"processed": False, "reason": "registration not found"})

	existing = frappe.db.get_value("Event Registration", registration, ["payment_status", "status"], as_dict=True)
	if existing and existing.payment_status == "Paid":
		return ok({"processed": True, "idempotent": True})

	result = _verify(
		registration,
		{
			"razorpay_payment_id": payment_id,
			"razorpay_order_id": order_id,
			"razorpay_signature": data.get("razorpay_signature"),
		},
	)
	return ok({"processed": True, "result": result})
