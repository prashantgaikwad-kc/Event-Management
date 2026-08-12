"""Payment gateway interface with Razorpay support."""

from __future__ import annotations

import hashlib
import hmac

import frappe
import requests
from frappe.utils import flt, now_datetime


def _razorpay_keys() -> tuple[str | None, str | None]:
	return frappe.conf.get("razorpay_key_id"), frappe.conf.get("razorpay_key_secret")


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
	body = f"{order_id}|{payment_id}".encode()
	expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, signature)


def create_payment_order(registration_name: str) -> dict:
	reg = frappe.get_doc("Event Registration", registration_name)
	if flt(reg.grand_total) <= 0:
		return {"required": False, "status": "Not Required"}

	currency = frappe.db.get_value("EM Event", reg.event, "currency") or "INR"
	key_id, key_secret = _razorpay_keys()
	order_id = f"order_{frappe.generate_hash(length=12)}"

	if key_id and key_secret:
		try:
			response = requests.post(
				"https://api.razorpay.com/v1/orders",
				auth=(key_id, key_secret),
				json={
					"amount": int(flt(reg.grand_total) * 100),
					"currency": currency,
					"receipt": reg.name,
					"notes": {"registration": reg.name},
				},
				timeout=20,
			)
			response.raise_for_status()
			order_id = response.json()["id"]
		except Exception as exc:
			frappe.log_error(title="Razorpay order creation failed", message=str(exc))
			if not frappe.conf.get("developer_mode"):
				frappe.throw("Unable to create payment order. Please try again later.")

	ref = frappe.get_doc(
		{
			"doctype": "Payment Reference",
			"registration": reg.name,
			"gateway": "Razorpay",
			"gateway_order_id": order_id,
			"amount": reg.grand_total,
			"currency": currency,
			"status": "Created",
			"created_at": now_datetime(),
		}
	)
	ref.insert(ignore_permissions=True)

	reg.db_set(
		{
			"payment_status": "Pending",
			"payment_gateway": "Razorpay",
			"payment_reference": order_id,
			"status": "Pending Payment",
		},
		update_modified=True,
	)

	result = {
		"required": True,
		"gateway": "Razorpay",
		"order_id": order_id,
		"amount": flt(reg.grand_total),
		"currency": currency,
		"payment_reference": ref.name,
	}
	if key_id:
		result["razorpay_key_id"] = key_id
	return result


def verify_payment(registration_name: str, payload: dict | None = None) -> dict:
	"""Server-side payment verification with Razorpay signature when configured."""
	payload = payload or {}
	reg = frappe.get_doc("Event Registration", registration_name)

	if flt(reg.grand_total) <= 0:
		_mark_paid(reg, gateway_payment_id="FREE")
		return {"status": "Paid", "registration": reg.name}

	payment_id = payload.get("razorpay_payment_id") or payload.get("payment_id")
	order_id = payload.get("razorpay_order_id") or payload.get("order_id") or reg.payment_reference
	signature = payload.get("razorpay_signature") or payload.get("signature")

	if not payment_id or not order_id:
		frappe.throw("Invalid payment payload")

	key_id, key_secret = _razorpay_keys()
	if key_secret and signature and signature != "demo":
		if not _verify_razorpay_signature(order_id, payment_id, signature, key_secret):
			frappe.throw("Invalid payment signature")
	elif not frappe.conf.get("developer_mode"):
		frappe.throw("Payment signature required")

	_mark_paid(reg, gateway_payment_id=payment_id, order_id=order_id, signature=signature)
	return {"status": "Paid", "registration": reg.name}


def _mark_paid(reg, gateway_payment_id: str, order_id: str | None = None, signature: str | None = None):
	if reg.payment_status == "Paid" and reg.status == "Confirmed":
		return

	reg.db_set(
		{
			"payment_status": "Paid",
			"status": "Confirmed",
			"payment_transaction_id": gateway_payment_id,
			"paid_at": now_datetime(),
		}
	)

	refs = frappe.get_all(
		"Payment Reference",
		filters={"registration": reg.name},
		pluck="name",
		limit=1,
	)
	if refs:
		frappe.db.set_value(
			"Payment Reference",
			refs[0],
			{
				"gateway_payment_id": gateway_payment_id,
				"gateway_signature": signature,
				"gateway_order_id": order_id or reg.payment_reference,
				"status": "Captured",
				"paid_at": now_datetime(),
			},
		)

	from event_management.utils.ticket import assign_qr_token, enqueue_ticket_email

	reg.reload()
	if not reg.qr_token_hash:
		assign_qr_token(reg)
	enqueue_ticket_email(reg.name)


def refund_payment(registration_name: str) -> dict:
	reg = frappe.get_doc("Event Registration", registration_name)
	if reg.payment_status != "Paid":
		return {"refunded": False, "reason": "Not paid"}
	reg.db_set({"payment_status": "Refunded", "status": "Refunded"})
	return {"refunded": True}
