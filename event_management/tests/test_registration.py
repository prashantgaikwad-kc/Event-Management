# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.api.attendee import create_registration
from event_management.utils.payments import verify_payment
from event_management.tests import make_event, make_ticket


class TestRegistration(FrappeTestCase):
	def test_free_ticket_confirms_immediately(self):
		event = make_event()
		ticket = make_ticket(
			event,
			price=0,
			capacity=5,
			code=f"F{frappe.generate_hash(length=4)}",
			title=f"Free{frappe.generate_hash(length=4)}",
		)
		result = create_registration(event=event.name, ticket_type=ticket.name)
		self.assertTrue(result["ok"])
		self.assertEqual(result["data"]["status"], "Confirmed")
		reg = frappe.get_doc("Event Registration", result["data"]["registration"])
		self.assertTrue(reg.qr_token_hash)

	def test_paid_ticket_pending_until_verified(self):
		event = make_event()
		ticket = make_ticket(
			event,
			price=500,
			capacity=5,
			code=f"P{frappe.generate_hash(length=4)}",
			title=f"Paid{frappe.generate_hash(length=4)}",
		)
		result = create_registration(event=event.name, ticket_type=ticket.name)
		self.assertTrue(result["ok"])
		self.assertEqual(result["data"]["status"], "Pending Payment")
		reg_name = result["data"]["registration"]

		verified = verify_payment(
			reg_name,
			{"razorpay_payment_id": "pay_test", "razorpay_order_id": result["data"]["payment"]["order_id"]},
		)
		self.assertEqual(verified["status"], "Paid")
		reg = frappe.get_doc("Event Registration", reg_name)
		self.assertEqual(reg.status, "Confirmed")
		self.assertEqual(reg.payment_status, "Paid")
		self.assertTrue(reg.qr_token_hash)
