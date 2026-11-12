"""Registration business rules: capacity, waitlist, deadlines and tickets.

Every operation that changes who holds a seat locks the event row
(``SELECT ... FOR UPDATE``) first, so concurrent requests for the same event are
serialized and capacity can never be exceeded.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    Ticket,
    User,
)
from app.services.tickets import issue_ticket, revoke_ticket

EVENT_NOT_FOUND_DETAIL = "Event not found."


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def registration_closes_at(event: Event) -> datetime:
    return as_utc(event.registration_deadline or event.start_time)


def is_registration_open(event: Event, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return event.status == EventStatus.PUBLISHED and now < registration_closes_at(event)


async def get_event_for_update(db: AsyncSession, event_id: UUID) -> Event:
    event = await db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND_DETAIL
        )
    return event


async def count_confirmed(db: AsyncSession, event_id: UUID) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == EventRegistrationStatus.CONFIRMED,
            )
        )
        or 0
    )


async def promote_waitlist(db: AsyncSession, event: Event) -> list[EventRegistration]:
    """Fill free seats from the waitlist (oldest first) and issue their tickets.

    The caller must hold the event row lock.
    """
    free_seats = event.capacity - await count_confirmed(db, event.id)
    if free_seats <= 0:
        return []
    promoted = list(
        (
            await db.scalars(
                select(EventRegistration)
                .where(
                    EventRegistration.event_id == event.id,
                    EventRegistration.status == EventRegistrationStatus.WAITLIST,
                )
                .order_by(EventRegistration.registered_at, EventRegistration.id)
                .limit(free_seats)
                .with_for_update()
            )
        ).all()
    )
    for registration in promoted:
        registration.status = EventRegistrationStatus.CONFIRMED
        await issue_ticket(db, registration)
    return promoted


async def register_user(db: AsyncSession, event_id: UUID, user: User) -> EventRegistration:
    event = await get_event_for_update(db, event_id)
    if event.status != EventStatus.PUBLISHED:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Registration is only open for published events.",
        )
    if not is_registration_open(event):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Registration for this event is closed.",
        )

    registration = await db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user.id,
        )
    )
    if registration is not None and registration.status != EventRegistrationStatus.CANCELLED:
        return registration

    registration_status = (
        EventRegistrationStatus.CONFIRMED
        if await count_confirmed(db, event_id) < event.capacity
        else EventRegistrationStatus.WAITLIST
    )
    if registration is None:
        registration = EventRegistration(
            event_id=event_id, user_id=user.id, status=registration_status
        )
        db.add(registration)
    else:
        registration.status = registration_status
        registration.registered_at = datetime.now(timezone.utc)
    await db.flush()

    if registration_status == EventRegistrationStatus.CONFIRMED:
        await issue_ticket(db, registration)

    await db.commit()
    await db.refresh(registration)
    return registration


async def cancel_registration(db: AsyncSession, event_id: UUID, user: User) -> EventRegistration:
    event = await get_event_for_update(db, event_id)
    registration = await db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user.id,
        )
    )
    if registration is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Event registration not found.",
        )
    if registration.status == EventRegistrationStatus.CANCELLED:
        return registration
    if event.status == EventStatus.COMPLETED:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Registrations cannot be cancelled after the event has ended.",
        )
    checked_in = await db.scalar(
        select(Ticket.checked_in_at).where(Ticket.registration_id == registration.id)
    )
    if checked_in is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="You have already checked in to this event.",
        )

    was_confirmed = registration.status == EventRegistrationStatus.CONFIRMED
    registration.status = EventRegistrationStatus.CANCELLED
    await revoke_ticket(db, registration.id)
    await db.flush()
    if was_confirmed and event.status in (EventStatus.PUBLISHED, EventStatus.IN_PROGRESS):
        await promote_waitlist(db, event)

    await db.commit()
    await db.refresh(registration)
    return registration


async def revoke_all_event_tickets(db: AsyncSession, event_id: UUID) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.event_id == event_id, Ticket.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
