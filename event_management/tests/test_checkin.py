# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.api.attendee import create_registration
from event_management.api.checkin import checkin_by_qr, checkin_by_registration
from event_management.utils.ticket import assign_qr_token
from event_management.tests import make_event, make_ticket


class TestCheckin(FrappeTestCase):
	def _confirmed_registration(self):
		event = make_event()
		ticket = make_ticket(
			event,
			capacity=10,
			price=0,
			code=f"C{frappe.generate_hash(length=4)}",
			title=f"T{frappe.generate_hash(length=4)}",
		)
		result = create_registration(event=event.name, ticket_type=ticket.name)
		reg_name = result["data"]["registration"]
		reg = frappe.get_doc("Event Registration", reg_name)
		token = assign_qr_token(reg)
		return reg_name, token, event

	def test_first_scan_valid(self):
		reg_name, token, _ = self._confirmed_registration()
		frappe.set_user("Administrator")
		result = checkin_by_qr(token)
		self.assertTrue(result["ok"])
		self.assertEqual(result["code"], "VALID")
		reg = frappe.get_doc("Event Registration", reg_name)
		self.assertEqual(reg.checked_in, 1)
		self.assertEqual(reg.checkin_count, 1)

	def test_duplicate_scan(self):
		reg_name, token, _ = self._confirmed_registration()
		frappe.set_user("Administrator")
		first = checkin_by_qr(token)
		self.assertTrue(first["ok"])
		second = checkin_by_qr(token)
		self.assertFalse(second["ok"])
		self.assertEqual(second["code"], "ALREADY_CHECKED_IN")
		reg = frappe.get_doc("Event Registration", reg_name)
		self.assertEqual(reg.checkin_count, 1)

	def test_cancelled_registration(self):
		reg_name, token, _ = self._confirmed_registration()
		frappe.db.set_value("Event Registration", reg_name, "status", "Cancelled")
		result = checkin_by_qr(token)
		self.assertFalse(result["ok"])
		self.assertEqual(result["code"], "CANCELLED")

	def test_unpaid_registration(self):
		reg_name, token, _ = self._confirmed_registration()
		frappe.db.set_value(
			"Event Registration",
			reg_name,
			{"status": "Pending Payment", "payment_status": "Pending"},
		)
		result = checkin_by_qr(token)
		self.assertFalse(result["ok"])
		self.assertEqual(result["code"], "UNPAID")

	def test_manual_checkin(self):
		reg_name, _, _ = self._confirmed_registration()
		result = checkin_by_registration(reg_name)
		self.assertTrue(result["ok"])
		self.assertEqual(result["code"], "VALID")
		dup = checkin_by_registration(reg_name)
		self.assertEqual(dup["code"], "ALREADY_CHECKED_IN")
