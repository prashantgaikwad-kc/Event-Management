# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

"""Sequential simulation of last-seat race (true threads need multi-worker DB sessions)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.api.attendee import create_registration
from event_management.utils import SoldOutError
from event_management.tests import make_event, make_ticket


class TestConcurrentCapacity(FrappeTestCase):
	def test_last_seat_only_one_succeeds(self):
		event = make_event()
		ticket = make_ticket(
			event,
			capacity=1,
			sold_count=0,
			price=0,
			code=f"LAST{frappe.generate_hash(length=3)}",
			title=f"Last{frappe.generate_hash(length=3)}",
		)

		first = create_registration(event=event.name, ticket_type=ticket.name)
		self.assertTrue(first["ok"])

		with self.assertRaises(SoldOutError):
			create_registration(event=event.name, ticket_type=ticket.name)

		ticket.reload()
		self.assertEqual(ticket.sold_count, 1)
		self.assertLessEqual(ticket.sold_count, ticket.capacity)
