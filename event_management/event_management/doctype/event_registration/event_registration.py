# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import secrets
import string

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class EventRegistration(Document):
	def before_insert(self):
		if not self.registration_time:
			self.registration_time = now_datetime()
		if not self.registration_reference:
			self.registration_reference = _public_reference(self.event)

	def validate(self):
		if not self.attendee_email:
			frappe.throw(_("Attendee email is required"))
		if self.attendee_user == "Guest":
			self.attendee_user = None


def _public_reference(event_name: str) -> str:
	"""Human-friendly public reference — never used as QR payload."""
	event = frappe.db.get_value("EM Event", event_name, ["slug", "event_start"], as_dict=True)
	prefix = (event.slug or "EVT").upper().replace("-", "")[:8]
	year = ""
	if event and event.event_start:
		year = str(frappe.utils.get_datetime(event.event_start).year)
	alphabet = string.ascii_uppercase + string.digits
	suffix = "".join(secrets.choice(alphabet) for _ in range(6))
	ref = f"{prefix}-{year}-{suffix}" if year else f"{prefix}-{suffix}"
	# Ensure uniqueness
	while frappe.db.exists("Event Registration", {"registration_reference": ref}):
		suffix = "".join(secrets.choice(alphabet) for _ in range(6))
		ref = f"{prefix}-{year}-{suffix}" if year else f"{prefix}-{suffix}"
	return ref
