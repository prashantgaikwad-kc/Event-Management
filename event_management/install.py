import frappe


ROLES = (
	"Event Organizer",
	"Event Gate Staff",
	"Event Attendee",
)


def after_install():
	_ensure_roles()
	_ensure_qr_secret()
	frappe.clear_cache()


def before_tests():
	_ensure_roles()
	_ensure_qr_secret()


def _ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			doc = frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role,
					"desk_access": 0 if role == "Event Attendee" else 1,
					"is_custom": 1,
				}
			)
			doc.insert(ignore_permissions=True)


def _ensure_qr_secret():
	"""Ensure a site-level HMAC secret exists for QR tokens."""
	from frappe.utils.password import get_encryption_key

	# Touch encryption key so site is ready for HMAC operations.
	get_encryption_key()
	if not frappe.conf.get("event_management_qr_secret"):
		import secrets

		frappe.conf.event_management_qr_secret = secrets.token_hex(32)
		# Persist into site_config when possible
		try:
			from frappe.installer import update_site_config

			update_site_config(
				"event_management_qr_secret",
				frappe.conf.event_management_qr_secret,
			)
		except Exception:
			pass
