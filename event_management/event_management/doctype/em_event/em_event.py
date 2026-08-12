# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class EMEvent(Document):
	def before_insert(self):
		if not self.created_by_user:
			self.created_by_user = frappe.session.user
		if not self.slug and self.event_name:
			self.slug = _slugify(self.event_name)

	def validate(self):
		self._normalize_slug()
		self._validate_schedule()
		self._validate_status_transition()

	def on_update(self):
		if self.has_value_changed("status"):
			if self.status in ("Published", "Registration Open") and not self.published_at:
				self.db_set("published_at", now_datetime(), update_modified=False)

	def _normalize_slug(self):
		if not self.slug:
			frappe.throw(_("Slug is required"))
		self.slug = _slugify(self.slug)
		existing = frappe.db.exists("EM Event", {"slug": self.slug, "name": ("!=", self.name)})
		if existing:
			frappe.throw(_("Slug {0} is already in use").format(self.slug))

	def _validate_schedule(self):
		if self.event_start and self.event_end:
			if get_datetime(self.event_start) >= get_datetime(self.event_end):
				frappe.throw(_("Event Start must be before Event End"))

		if self.registration_start and self.registration_end:
			if get_datetime(self.registration_start) >= get_datetime(self.registration_end):
				frappe.throw(_("Registration Start must be before Registration End"))

		if self.registration_end and self.event_start:
			if get_datetime(self.registration_end) > get_datetime(self.event_start):
				frappe.throw(_("Registration End must not be later than Event Start"))

		if self.allow_cancellation and self.cancellation_deadline and self.event_start:
			if get_datetime(self.cancellation_deadline) > get_datetime(self.event_start):
				frappe.throw(_("Cancellation deadline should be on or before Event Start"))

	def _validate_status_transition(self):
		if self.is_new():
			return
		old = self.get_doc_before_save()
		if not old:
			return
		# Cancellation allowed from several states
		if self.status == "Cancelled":
			return
		# Prevent moving out of Cancelled / Completed casually
		if old.status in ("Cancelled", "Completed") and self.status != old.status:
			frappe.throw(_("Cannot change status from {0}").format(old.status))


def _slugify(value: str) -> str:
	value = (value or "").strip().lower()
	value = re.sub(r"[^a-z0-9]+", "-", value)
	return value.strip("-")
