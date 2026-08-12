"""Signed, non-guessable QR ticket tokens.

Token format: v1.<base64url(payload_json)>.<hex(hmac_sha256)>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

import frappe
from frappe.utils import cint, get_datetime, now_datetime

from event_management.utils import InvalidTokenError


TOKEN_VERSION = 1


def _b64url_encode(raw: bytes) -> str:
	return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
	padding = "=" * (-len(value) % 4)
	return base64.urlsafe_b64decode(value + padding)


def get_qr_secret() -> str:
	secret = frappe.conf.get("event_management_qr_secret")
	if secret:
		return secret
	# Fallback: derive from site encryption key (still server-side only)
	from frappe.utils.password import get_encryption_key

	return hashlib.sha256(get_encryption_key().encode()).hexdigest()


def hash_token(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(registration_name: str, expires_at=None) -> tuple[str, dict[str, Any]]:
	"""Return (token, metadata) for a registration."""
	now = now_datetime()
	nonce = secrets.token_urlsafe(24)
	payload = {
		"rid": registration_name,
		"nonce": nonce,
		"iat": int(now.timestamp()),
		"ver": TOKEN_VERSION,
	}
	if expires_at:
		payload["exp"] = int(get_datetime(expires_at).timestamp())

	body = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
	signature = hmac.new(
		get_qr_secret().encode("utf-8"),
		f"v{TOKEN_VERSION}.{body}".encode("utf-8"),
		hashlib.sha256,
	).hexdigest()
	token = f"v{TOKEN_VERSION}.{body}.{signature}"
	meta = {
		"qr_token_hash": hash_token(token),
		"qr_token_version": TOKEN_VERSION,
		"qr_token_issued_at": now,
		"qr_token_expires_at": expires_at,
		"nonce": nonce,
	}
	return token, meta


def parse_and_verify_token(token: str) -> dict[str, Any]:
	if not token or not isinstance(token, str):
		raise InvalidTokenError("Invalid or expired ticket")

	parts = token.strip().split(".")
	if len(parts) != 3:
		raise InvalidTokenError("Invalid or expired ticket")

	version_part, body, signature = parts
	if not version_part.startswith("v"):
		raise InvalidTokenError("Invalid or expired ticket")

	try:
		version = cint(version_part[1:])
	except Exception as exc:
		raise InvalidTokenError("Invalid or expired ticket") from exc

	if version != TOKEN_VERSION:
		raise InvalidTokenError("Invalid or expired ticket")

	expected = hmac.new(
		get_qr_secret().encode("utf-8"),
		f"{version_part}.{body}".encode("utf-8"),
		hashlib.sha256,
	).hexdigest()

	if not hmac.compare_digest(expected, signature):
		raise InvalidTokenError("Invalid or expired ticket")

	try:
		payload = json.loads(_b64url_decode(body))
	except Exception as exc:
		raise InvalidTokenError("Invalid or expired ticket") from exc

	if not isinstance(payload, dict) or not payload.get("rid") or not payload.get("nonce"):
		raise InvalidTokenError("Invalid or expired ticket")

	if payload.get("exp"):
		now_ts = int(now_datetime().timestamp())
		if now_ts > cint(payload["exp"]):
			raise InvalidTokenError("Invalid or expired ticket")

	payload["_token_hash"] = hash_token(token)
	payload["_version"] = version
	return payload
