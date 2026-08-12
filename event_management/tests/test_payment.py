# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.utils.payments import create_payment_order, verify_payment
from event_management.tests import make_event, make_ticket


class TestPayment(FrappeTestCase):
	def test_verify_is_idempotent(self):
		event = make_event()
		ticket = make_ticket(
			event,
			price=100,
			capacity=5,
			code=f"PAY{frappe.generate_hash(length=3)}",
			title=f"Pay{frappe.generate_hash(length=3)}",
		)
		reg = frappe.get_doc(
			{
				"doctype": "Event Registration",
				"event": event.name,
				"attendee_user": "Administrator",
				"attendee_name": "Admin",
				"attendee_email": "admin@example.com",
				"ticket_type": ticket.name,
				"ticket_price": 100,
				"addon_total": 0,
				"subtotal": 100,
				"grand_total": 100,
				"status": "Pending Payment",
				"payment_status": "Pending",
			}
		)
		reg.insert(ignore_permissions=True)
		order = create_payment_order(reg.name)
		first = verify_payment(
			reg.name,
			{"razorpay_payment_id": "pay_1", "razorpay_order_id": order["order_id"], "signature": "x"},
		)
		second = verify_payment(
			reg.name,
			{"razorpay_payment_id": "pay_1", "razorpay_order_id": order["order_id"], "signature": "x"},
		)
		self.assertEqual(first["status"], "Paid")
		self.assertEqual(second["status"], "Paid")
		reg.reload()
		self.assertEqual(reg.status, "Confirmed")
