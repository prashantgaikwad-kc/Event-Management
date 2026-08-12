# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import time

import frappe
from frappe.tests.utils import FrappeTestCase

from event_management.utils import InvalidTokenError
from event_management.utils.token import hash_token, issue_token, parse_and_verify_token
from event_management.tests import ensure_roles


class TestToken(FrappeTestCase):
	def setUp(self):
		ensure_roles()
		frappe.conf.event_management_qr_secret = "test-secret-key-for-hmac"

	def test_valid_token(self):
		token, meta = issue_token("REG-TEST-1")
		payload = parse_and_verify_token(token)
		self.assertEqual(payload["rid"], "REG-TEST-1")
		self.assertEqual(meta["qr_token_hash"], hash_token(token))

	def test_tampered_token(self):
		token, _ = issue_token("REG-TEST-2")
		parts = token.split(".")
		# Tamper payload
		tampered = f"{parts[0]}.{parts[1][:-2]}ab.{parts[2]}"
		with self.assertRaises(InvalidTokenError):
			parse_and_verify_token(tampered)

	def test_random_token_rejected(self):
		with self.assertRaises(InvalidTokenError):
			parse_and_verify_token("v1.notreal.deadbeef")

	def test_expired_token(self):
		from datetime import timedelta

		from frappe.utils import now_datetime

		token, _ = issue_token("REG-TEST-3", expires_at=now_datetime() - timedelta(seconds=5))
		with self.assertRaises(InvalidTokenError):
			parse_and_verify_token(token)
