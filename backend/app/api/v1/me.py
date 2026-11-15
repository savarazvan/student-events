"""Endpoints for the signed-in student: personal schedule and tickets."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Event, EventRegistration, EventRegistrationStatus, Ticket, User
from app.schemas.ticket import MyRegistrationResponse, TicketEventSummary, TicketResponse
from app.services.tickets import (
    TicketState,
    create_ticket_token,
    render_qr_svg,
    ticket_state,
)

router = APIRouter(prefix="/me", tags=["Me"])
TICKET_NOT_FOUND_DETAIL = "Ticket not found."


def _event_summary(event: Event) -> TicketEventSummary:
    return TicketEventSummary(
        id=event.id,
        title=event.title,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        status=event.status,
        category=event.category,
        organization_id=event.organization_id,
    )


async def _get_own_ticket(db: AsyncSession, ticket_id: UUID, user: User) -> tuple[Ticket, Event]:
    row = (
        await db.execute(
            select(Ticket, Event)
            .join(Event, Event.id == Ticket.event_id)
            .where(Ticket.id == ticket_id, Ticket.user_id == user.id)
        )
    ).first()
    if row is None:
        # Same answer for "does not exist" and "belongs to someone else".
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=TICKET_NOT_FOUND_DETAIL)
    return row[0], row[1]


@router.get("/registrations", response_model=list[MyRegistrationResponse])
async def list_my_registrations(
    upcoming: bool = Query(default=False, description="Only events that have not ended yet"),
    include_cancelled: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyRegistrationResponse]:
    """The student's personal schedule, ordered by event start time."""
    query = (
        select(EventRegistration, Event, Ticket)
        .join(Event, Event.id == EventRegistration.event_id)
        .outerjoin(Ticket, Ticket.registration_id == EventRegistration.id)
        .where(EventRegistration.user_id == current_user.id)
        .order_by(Event.start_time, Event.id)
    )
    if not include_cancelled:
        query = query.where(EventRegistration.status != EventRegistrationStatus.CANCELLED)
    if upcoming:
        query = query.where(Event.end_time > datetime.now(timezone.utc))

    return [
        MyRegistrationResponse(
            id=registration.id,
            status=registration.status,
            registered_at=registration.registered_at,
            ticket_id=ticket.id if ticket else None,
            ticket_state=ticket_state(ticket) if ticket else None,
            checked_in_at=ticket.checked_in_at if ticket else None,
            event=_event_summary(event),
        )
        for registration, event, ticket in (await db.execute(query)).all()
    ]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_my_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    ticket, event = await _get_own_ticket(db, ticket_id, current_user)
    state = ticket_state(ticket)
    return TicketResponse(
        id=ticket.id,
        registration_id=ticket.registration_id,
        state=state,
        issued_at=ticket.issued_at,
        checked_in_at=ticket.checked_in_at,
        qr_token=None if state == TicketState.REVOKED else create_ticket_token(ticket),
        event=_event_summary(event),
    )


@router.get(
    "/tickets/{ticket_id}/qr.svg",
    response_class=Response,
    responses={200: {"content": {"image/svg+xml": {}}}},
)
async def get_my_ticket_qr(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Ready-to-display QR code (SVG) for the ticket."""
    ticket, _ = await _get_own_ticket(db, ticket_id, current_user)
    if ticket.revoked_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_410_GONE, detail="Ticket has been revoked."
        )
    return Response(
        content=render_qr_svg(create_ticket_token(ticket)),
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, no-store"},
    )
