"""Ticket verification: the page a phone opens after scanning a ticket QR code."""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.api.event_access import is_event_manager
from app.api.v1.me import event_summary
from app.core.database import get_db
from app.models.models import Event, Ticket, User
from app.schemas.ticket import TicketVerificationResponse
from app.services.attendance import check_in_closed_reason
from app.services.tickets import (
    InvalidTicketToken,
    TicketState,
    codes_match,
    decode_ticket_token,
    ticket_state,
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/verify", response_model=TicketVerificationResponse)
async def verify_ticket(
    token: str = Query(min_length=1, max_length=4096, description="Token or ticket-check URL"),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketVerificationResponse:
    """Check a scanned ticket. Public, but the attendee's name is shown only to the
    ticket holder and the event's organizers, who also learn whether they can
    check the ticket in right now."""
    try:
        ticket_id, event_id, code = decode_ticket_token(token)
    except InvalidTicketToken:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="This is not a valid ticket."
        ) from None
    row = (
        await db.execute(
            select(Ticket, Event, User.full_name)
            .join(Event, Event.id == Ticket.event_id)
            .join(User, User.id == Ticket.user_id)
            .where(Ticket.id == ticket_id, Ticket.event_id == event_id)
        )
    ).first()
    if row is None or not codes_match(row[0].code, code):
        # A re-issued ticket gets a new code, so old QR codes stop working.
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="This is not a valid ticket."
        )
    ticket, event, attendee_name = row

    is_manager = await is_event_manager(db, current_user, event)
    is_holder = current_user is not None and current_user.id == ticket.user_id
    state = ticket_state(ticket)

    reason: str | None = None
    if not is_manager:
        reason = "Only the event's organizers can check tickets in."
    elif state == TicketState.REVOKED:
        reason = "Ticket has been revoked (registration cancelled)."
    elif state == TicketState.USED:
        reason = "Ticket already checked in."
    else:
        reason = check_in_closed_reason(event)

    return TicketVerificationResponse(
        ticket_id=ticket.id,
        state=state,
        event=event_summary(event),
        checked_in_at=ticket.checked_in_at,
        attendee_name=attendee_name if (is_manager or is_holder) else None,
        can_check_in=reason is None,
        check_in_unavailable_reason=reason,
    )
