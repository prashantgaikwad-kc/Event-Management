"""Ticket helpers: QR image generation, PDF, and email."""

from __future__ import annotations

import io

import frappe
from frappe.utils.password import decrypt, encrypt

from event_management.utils.token import issue_token

TICKET_PRINT_FORMAT = "Event Ticket"


def assign_qr_token(registration_doc) -> str:
	"""Issue a signed QR token once; store hash + encrypted token for re-display."""
	existing_enc = registration_doc.get("qr_token_encrypted") or frappe.db.get_value(
		"Event Registration", registration_doc.name, "qr_token_encrypted"
	)
	existing_hash = registration_doc.get("qr_token_hash") or frappe.db.get_value(
		"Event Registration", registration_doc.name, "qr_token_hash"
	)
	if existing_enc and existing_hash:
		try:
			return decrypt(existing_enc)
		except Exception:
			pass

	token, meta = issue_token(registration_doc.name, expires_at=None)
	registration_doc.db_set(
		{
			"qr_token_hash": meta["qr_token_hash"],
			"qr_token_version": meta["qr_token_version"],
			"qr_token_issued_at": meta["qr_token_issued_at"],
			"qr_token_expires_at": meta["qr_token_expires_at"],
			"qr_token_encrypted": encrypt(token),
		},
		update_modified=False,
	)
	return token


def generate_qr_png_base64(token: str) -> str:
	import base64

	import qrcode

	img = qrcode.make(token)
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	return base64.b64encode(buf.getvalue()).decode("ascii")


def get_qr_html_for_registration(registration_name: str) -> str:
	reg = frappe.get_doc("Event Registration", registration_name)
	if reg.status != "Confirmed":
		return ""
	token = assign_qr_token(reg)
	b64 = generate_qr_png_base64(token)
	return f'<img src="data:image/png;base64,{b64}" alt="Ticket QR" style="width:180px;height:180px;" />'


def generate_ticket_pdf(registration_name: str) -> bytes:
	"""Render the Event Ticket print format as PDF bytes."""
	from frappe.utils.pdf import get_pdf
	from frappe.utils.print_utils import get_print_html

	html = get_print_html(
		frappe.get_doc("Event Registration", registration_name),
		print_format=TICKET_PRINT_FORMAT,
		no_letterhead=1,
	)
	return get_pdf(html)


def ticket_pdf_filename(registration_name: str) -> str:
	ref = frappe.db.get_value("Event Registration", registration_name, "registration_reference")
	return f"ticket-{ref or registration_name}.pdf"


def enqueue_ticket_email(registration_name: str):
	"""Queue non-blocking ticket email with PDF attachment."""
	frappe.enqueue(
		"event_management.utils.ticket.send_ticket_email",
		registration_name=registration_name,
		queue="short",
		enqueue_after_commit=True,
	)


def send_ticket_email(registration_name: str):
	reg = frappe.get_doc("Event Registration", registration_name)
	if not reg.attendee_email or reg.status != "Confirmed":
		return

	event_name = frappe.db.get_value("EM Event", reg.event, "event_name") or reg.event
	attachments = []
	try:
		pdf_bytes = generate_ticket_pdf(registration_name)
		attachments.append(
			{
				"fname": ticket_pdf_filename(registration_name),
				"fcontent": pdf_bytes,
			}
		)
	except Exception:
		frappe.log_error(title="Ticket PDF generation failed", message=registration_name)

	frappe.sendmail(
		recipients=[reg.attendee_email],
		subject=f"Your Ticket — {event_name}",
		message=f"""
			<p>Hi {frappe.utils.escape_html(reg.attendee_name)},</p>
			<p>Your registration <b>{frappe.utils.escape_html(reg.registration_reference or reg.name)}</b> is confirmed.</p>
			<p>Your ticket PDF is attached. You can also view your QR code in the attendee portal.</p>
		""",
		attachments=attachments or None,
		now=False,
	)
