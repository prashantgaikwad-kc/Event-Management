"""Database transaction helpers."""

from __future__ import annotations

from contextlib import contextmanager

import frappe


@contextmanager
def atomic(savepoint: str = "em_atomic"):
	"""Rollback to savepoint on error; safe inside Frappe tests and HTTP requests."""
	frappe.db.savepoint(savepoint)
	try:
		yield
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
