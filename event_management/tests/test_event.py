# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.tests import make_event


class TestEvent(FrappeTestCase):
	def test_event_start_before_end(self):
		from datetime import timedelta

		from frappe.utils import now_datetime

		now = now_datetime()
		doc = frappe.get_doc(
			{
				"doctype": "EM Event",
				"event_name": "Bad Schedule",
				"slug": f"bad-{frappe.generate_hash(length=5)}",
				"status": "Draft",
				"event_start": now + timedelta(days=2),
				"event_end": now + timedelta(days=1),
				"currency": "INR",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_unique_slug(self):
		e1 = make_event(slug=f"unique-{frappe.generate_hash(length=5)}")
		doc = frappe.get_doc(
			{
				"doctype": "EM Event",
				"event_name": "Copy",
				"slug": e1.slug,
				"status": "Draft",
				"event_start": e1.event_start,
				"event_end": e1.event_end,
				"currency": "INR",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)
