# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime


class EventAddon(Document):
	def validate(self):
		if cint(self.stock) < 0:
			frappe.throw(_("Add-on stock must be non-negative"))
		if cint(self.sold_count) < 0:
			frappe.throw(_("Sold count cannot be negative"))
		if cint(self.sold_count) > cint(self.stock):
			frappe.throw(_("Sold count cannot exceed stock"))

		if self.sales_start and self.sales_end:
			if get_datetime(self.sales_start) >= get_datetime(self.sales_end):
				frappe.throw(_("Sales Start must be before Sales End"))

		self.code = (self.code or "").strip().upper()
		if frappe.db.exists(
			"Event Addon",
			{"event": self.event, "code": self.code, "name": ("!=", self.name)},
		):
			frappe.throw(_("Add-on code {0} already exists for this event").format(self.code))

		if frappe.db.exists(
			"Event Addon",
			{"event": self.event, "title": self.title, "name": ("!=", self.name)},
		):
			frappe.throw(_("Add-on title {0} already exists for this event").format(self.title))

	@property
	def available_stock(self) -> int:
		return cint(self.stock) - cint(self.sold_count)
