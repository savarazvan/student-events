"""Attendance statistics and the check-in window rule."""

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    Ticket,
)
from app.schemas.ticket import AttendanceStatsResponse
from app.services.registrations import as_utc


def checkin_opens_before() -> timedelta:
    return timedelta(minutes=int(os.getenv("CHECKIN_OPENS_MINUTES_BEFORE", "60")))


def check_in_closed_reason(event: Event, now: datetime | None = None) -> str | None:
    """Why tickets for ``event`` cannot be checked in right now, or None when they can."""
    if event.status not in (EventStatus.PUBLISHED, EventStatus.IN_PROGRESS):
        return f"Check-in is not possible for a {event.status.value} event."
    now = now or datetime.now(timezone.utc)
    opens_at = as_utc(event.start_time) - checkin_opens_before()
    if now < opens_at:
        return f"Check-in opens at {opens_at.isoformat()}."
    if now > as_utc(event.end_time):
        return "Check-in has closed: the event has ended."
    return None


async def attendance_stats(db: AsyncSession, event: Event) -> AttendanceStatsResponse:
    counts = dict(
        (
            await db.execute(
                select(EventRegistration.status, func.count())
                .where(EventRegistration.event_id == event.id)
                .group_by(EventRegistration.status)
            )
        ).all()
    )
    checked_in = (
        await db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id == event.id,
                Ticket.revoked_at.is_(None),
                Ticket.checked_in_at.is_not(None),
            )
        )
        or 0
    )
    confirmed = counts.get(EventRegistrationStatus.CONFIRMED, 0)
    return AttendanceStatsResponse(
        event_id=event.id,
        capacity=event.capacity,
        confirmed=confirmed,
        waitlisted=counts.get(EventRegistrationStatus.WAITLIST, 0),
        cancelled=counts.get(EventRegistrationStatus.CANCELLED, 0),
        checked_in=checked_in,
        not_checked_in=max(confirmed - checked_in, 0),
        attendance_rate=round(checked_in / confirmed, 4) if confirmed else 0.0,
        spots_left=max(event.capacity - confirmed, 0),
    )
