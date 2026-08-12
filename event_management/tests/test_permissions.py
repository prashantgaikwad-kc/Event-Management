# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.tests import ensure_roles
from event_management.utils.permissions import is_gate_staff, is_organizer


class TestPermissions(FrappeTestCase):
	def setUp(self):
		ensure_roles()

	def test_administrator_is_organizer(self):
		frappe.set_user("Administrator")
		self.assertTrue(is_organizer())
		self.assertTrue(is_gate_staff())
