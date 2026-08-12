# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.api.attendee import create_registration
from event_management.utils import SoldOutError
from event_management.tests import make_addon, make_event, make_ticket


class TestCapacity(FrappeTestCase):
	def test_within_capacity(self):
		event = make_event()
		ticket = make_ticket(event, capacity=10, sold_count=9, price=0, code="T1", title="T1")
		frappe.set_user("Administrator")
		result = create_registration(event=event.name, ticket_type=ticket.name)
		self.assertTrue(result["ok"])
		ticket.reload()
		self.assertEqual(ticket.sold_count, 10)

	def test_at_capacity_rejected(self):
		event = make_event()
		ticket = make_ticket(event, capacity=10, sold_count=10, price=0, code="T2", title="T2")
		with self.assertRaises(SoldOutError):
			create_registration(event=event.name, ticket_type=ticket.name)
		ticket.reload()
		self.assertEqual(ticket.sold_count, 10)

	def test_cancellation_frees_capacity(self):
		from event_management.api.attendee import cancel_registration

		event = make_event()
		ticket = make_ticket(event, capacity=10, sold_count=9, price=0, code="T3", title="T3")
		result = create_registration(event=event.name, ticket_type=ticket.name)
		reg_name = result["data"]["registration"]
		ticket.reload()
		self.assertEqual(ticket.sold_count, 10)

		cancel_registration(reg_name)
		ticket.reload()
		self.assertEqual(ticket.sold_count, 9)

		result2 = create_registration(event=event.name, ticket_type=ticket.name)
		self.assertTrue(result2["ok"])
		ticket.reload()
		self.assertEqual(ticket.sold_count, 10)

	def test_addon_stock_enforcement(self):
		from event_management.utils import AddonUnavailableError

		event = make_event()
		ticket = make_ticket(event, capacity=10, price=0, code="T4", title="T4")
		addon = make_addon(event, stock=5, sold_count=5, price=0, code="A1", title="A1")
		with self.assertRaises(AddonUnavailableError):
			create_registration(event=event.name, ticket_type=ticket.name, addon_ids=[addon.name])
		ticket.reload()
		addon.reload()
		self.assertEqual(ticket.sold_count, 0)
		self.assertEqual(addon.sold_count, 5)

	def test_mixed_ticket_addon_rollback(self):
		from event_management.utils import AddonUnavailableError

		event = make_event()
		ticket = make_ticket(event, capacity=10, price=0, code="T5", title="T5")
		ok_addon = make_addon(event, stock=5, sold_count=0, price=0, code="OK", title="OK")
		bad_addon = make_addon(event, stock=1, sold_count=1, price=0, code="BAD", title="BAD")
		with self.assertRaises(AddonUnavailableError):
			create_registration(
				event=event.name,
				ticket_type=ticket.name,
				addon_ids=[ok_addon.name, bad_addon.name],
			)
		ticket.reload()
		ok_addon.reload()
		self.assertEqual(ticket.sold_count, 0)
		self.assertEqual(ok_addon.sold_count, 0)
