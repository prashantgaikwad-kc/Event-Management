# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class EventRegistrationItem(Document):
	def validate(self):
		if cint(self.qty) != 1:
			frappe.throw(_("Add-on quantity must be 1 for MVP"))
		self.amount = flt(self.unit_price) * cint(self.qty)
