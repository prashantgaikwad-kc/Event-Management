"""Seed DevCon demo data.

Run:
  cd frappe-bench
  bench --site events.localhost execute event_management.seed_devcon.run
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_to_date, now_datetime


def run():
	frappe.set_user("Administrator")
	from event_management.install import after_install

	after_install()

	_ensure_user("priya@devcon.local", "Priya Shah", ["Event Organizer", "System Manager"], "priya1234")
	_ensure_user("raj@devcon.local", "Raj Gate", ["Event Gate Staff"], "raj1234")
	_ensure_user("attendee@devcon.local", "Asha Attendee", ["Event Attendee"], "asha1234")

	if frappe.db.get_value("EM Event", {"slug": "devcon-2026"}, "name"):
		frappe.db.commit()
		_print_done()
		return

	now = now_datetime()
	event_start = add_days(now, 14)
	event_end = add_to_date(event_start, hours=8)
	event = frappe.get_doc(
		{
			"doctype": "EM Event",
			"event_name": "DevCon 2026",
			"slug": "devcon-2026",
			"status": "Registration Open",
			"short_description": "One-day tech conference with talks, workshops, and networking.",
			"description": "<p>DevCon brings builders together for a full day of talks and workshops.</p>",
			"venue_name": "Pune Convention Center",
			"venue_address": "Baner Road, Pune",
			"city": "Pune",
			"event_start": event_start,
			"event_end": event_end,
			"registration_start": add_days(now, -2),
			"registration_end": add_days(now, 13),
			"currency": "INR",
			"allow_cancellation": 1,
			"cancellation_deadline": add_days(now, 12),
			"is_featured": 1,
		}
	)
	event.insert(ignore_permissions=True)

	for t in [
		{"title": "Early-Bird", "code": "EARLY", "price": 999, "capacity": 50, "sort_order": 1},
		{"title": "Regular", "code": "REG", "price": 1499, "capacity": 100, "sort_order": 2},
		{"title": "Student", "code": "STU", "price": 499, "capacity": 40, "sort_order": 3},
	]:
		frappe.get_doc(
			{"doctype": "Event Ticket Type", "event": event.name, "is_active": 1, **t}
		).insert(ignore_permissions=True)

	for a in [
		{"title": "Lunch", "code": "LUNCH", "price": 299, "stock": 80},
		{"title": "Workshop", "code": "WORKSHOP", "price": 799, "stock": 30},
		{"title": "T-Shirt", "code": "TSHIRT", "price": 399, "stock": 50},
	]:
		frappe.get_doc(
			{"doctype": "Event Addon", "event": event.name, "is_active": 1, **a}
		).insert(ignore_permissions=True)

	frappe.db.commit()
	_print_done()


def _ensure_user(email: str, full_name: str, roles: list[str], password: str):
	user = frappe.get_doc("User", email) if frappe.db.exists("User", email) else frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name.split(" ", 1)[0],
			"last_name": full_name.split(" ", 1)[-1] if " " in full_name else "",
			"send_welcome_email": 0,
			"user_type": "Website User" if roles == ["Event Attendee"] else "System User",
		}
	)
	if user.is_new():
		user.insert(ignore_permissions=True)
	for role in roles:
		user.add_roles(role)
	user.save(ignore_permissions=True)
	frappe.utils.password.update_password(email, password)


def _print_done():
	print("DevCon demo data seeded.")
