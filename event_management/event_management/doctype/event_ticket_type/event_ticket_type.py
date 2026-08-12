# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime


class EventTicketType(Document):
	def validate(self):
		if cint(self.capacity) <= 0:
			frappe.throw(_("Ticket capacity must be positive"))
		if cint(self.sold_count) < 0 or cint(self.reserved_count) < 0:
			frappe.throw(_("Sold/reserved counts cannot be negative"))
		if cint(self.sold_count) + cint(self.reserved_count) > cint(self.capacity):
			frappe.throw(_("Sold + reserved cannot exceed capacity"))

		if self.sales_start and self.sales_end:
			if get_datetime(self.sales_start) >= get_datetime(self.sales_end):
				frappe.throw(_("Sales Start must be before Sales End"))

		self.code = (self.code or "").strip().upper()
		if frappe.db.exists(
			"Event Ticket Type",
			{"event": self.event, "code": self.code, "name": ("!=", self.name)},
		):
			frappe.throw(_("Ticket code {0} already exists for this event").format(self.code))

		if frappe.db.exists(
			"Event Ticket Type",
			{"event": self.event, "title": self.title, "name": ("!=", self.name)},
		):
			frappe.throw(_("Ticket title {0} already exists for this event").format(self.title))

	@property
	def available_count(self) -> int:
		return cint(self.capacity) - cint(self.sold_count) - cint(self.reserved_count)
