# Copyright (c) 2026, Koecent Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe


def get_filters():
	return [
		{
			"fieldname": "event",
			"label": "Event",
			"fieldtype": "Link",
			"options": "EM Event",
		}
	]
