"""Ticket issuing, revocation, signed QR tokens and QR rendering."""

import hashlib
import hmac
import io
import os
import secrets
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import parse_qs, quote, urlsplit
from uuid import UUID

import jwt
import qrcode
import qrcode.image.svg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import JWT_ALGORITHM, _secret_key
from app.models.models import EventRegistration, Ticket

TICKET_TOKEN_TYPE = "ticket"
# Frontend page a phone camera opens when it scans the QR code.
TICKET_CHECK_PATH = "/ticket-check"


class TicketState(str, Enum):
    VALID = "VALID"
    USED = "USED"
    REVOKED = "REVOKED"


class InvalidTicketToken(Exception):
    """The scanned QR payload is not a ticket token signed by this server."""


def _ticket_secret() -> str:
    explicit = os.getenv("TICKET_SECRET")
    if explicit:
        return explicit
    # Derive a dedicated key so a ticket token can never be used as an access token.
    return hmac.new(_secret_key().encode(), b"ticket-tokens", hashlib.sha256).hexdigest()


def new_ticket_code() -> str:
    return secrets.token_urlsafe(24)


def ticket_state(ticket: Ticket) -> TicketState:
    if ticket.revoked_at is not None:
        return TicketState.REVOKED
    if ticket.checked_in_at is not None:
        return TicketState.USED
    return TicketState.VALID


def create_ticket_token(ticket: Ticket) -> str:
    """Signed payload encoded in the QR code. Contains no personal data."""
    payload = {
        "typ": TICKET_TOKEN_TYPE,
        "tid": str(ticket.id),
        "eid": str(ticket.event_id),
        "code": ticket.code,
    }
    return jwt.encode(payload, _ticket_secret(), algorithm=JWT_ALGORITHM)


def ticket_check_url(token: str) -> str:
    """URL encoded in the QR code.

    A regular phone camera opens it in the browser (ticket verification page,
    with a check-in button for organizers) instead of searching for raw text.
    """
    base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}{TICKET_CHECK_PATH}?token={quote(token, safe='')}"


def extract_ticket_token(scanned: str) -> str:
    """Accept either the bare token or the full ticket-check URL from the QR code."""
    scanned = scanned.strip()
    if "://" in scanned or scanned.startswith(TICKET_CHECK_PATH):
        values = parse_qs(urlsplit(scanned).query).get("token")
        if values:
            return values[0].strip()
    return scanned


def decode_ticket_token(token: str) -> tuple[UUID, UUID, str]:
    """Return (ticket_id, event_id, code) or raise InvalidTicketToken.

    ``token`` may be the bare signed token or the ticket-check URL containing it.
    """
    try:
        payload = jwt.decode(
            extract_ticket_token(token), _ticket_secret(), algorithms=[JWT_ALGORITHM]
        )
        if payload.get("typ") != TICKET_TOKEN_TYPE:
            raise InvalidTicketToken
        return UUID(payload["tid"]), UUID(payload["eid"]), str(payload["code"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError, AttributeError):
        raise InvalidTicketToken from None


def codes_match(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected.encode(), provided.encode())


def render_qr_svg(data: str) -> bytes:
    image = qrcode.make(
        data,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue()


async def issue_ticket(db: AsyncSession, registration: EventRegistration) -> Ticket:
    """Create the registration's ticket, or re-activate it with a fresh code."""
    ticket = await db.scalar(select(Ticket).where(Ticket.registration_id == registration.id))
    now = datetime.now(timezone.utc)
    if ticket is None:
        ticket = Ticket(
            registration_id=registration.id,
            event_id=registration.event_id,
            user_id=registration.user_id,
            code=new_ticket_code(),
            issued_at=now,
        )
        db.add(ticket)
    elif ticket.revoked_at is not None:
        ticket.code = new_ticket_code()
        ticket.issued_at = now
        ticket.revoked_at = None
        ticket.checked_in_at = None
        ticket.checked_in_by_id = None
    return ticket


async def revoke_ticket(db: AsyncSession, registration_id: UUID) -> None:
    ticket = await db.scalar(select(Ticket).where(Ticket.registration_id == registration_id))
    if ticket is not None and ticket.revoked_at is None:
        ticket.revoked_at = datetime.now(timezone.utc)
