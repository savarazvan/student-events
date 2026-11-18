"""Post-event feedback from attendees and the organizer's event report."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.event_access import get_event_or_404, get_visible_event, require_event_manager
from app.core.database import get_db
from app.models.models import EventFeedback, EventStatus, Ticket, User
from app.schemas.feedback import (
    EventReportResponse,
    FeedbackComment,
    FeedbackCreate,
    FeedbackResponse,
)
from app.services.attendance import attendance_stats

router = APIRouter(prefix="/events", tags=["Feedback"])


@router.put("/{event_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    event_id: UUID,
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventFeedback:
    """Create or update the current user's feedback.

    Only attendees who checked in may rate, and only once the event is COMPLETED,
    so ratings reflect people who actually took part.
    """
    event = await get_visible_event(db, event_id, current_user)
    if event.status != EventStatus.COMPLETED:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Feedback opens once the event is completed.",
        )
    attended = await db.scalar(
        select(Ticket.id).where(
            Ticket.event_id == event_id,
            Ticket.user_id == current_user.id,
            Ticket.revoked_at.is_(None),
            Ticket.checked_in_at.is_not(None),
        )
    )
    if attended is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only attendees who checked in can leave feedback.",
        )

    feedback = await db.scalar(
        select(EventFeedback).where(
            EventFeedback.event_id == event_id, EventFeedback.user_id == current_user.id
        )
    )
    if feedback is None:
        feedback = EventFeedback(event_id=event_id, user_id=current_user.id, rating=payload.rating)
        db.add(feedback)
    feedback.rating = payload.rating
    feedback.comment = payload.comment
    feedback.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.get("/{event_id}/feedback/me", response_model=FeedbackResponse)
async def get_my_feedback(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventFeedback:
    feedback = await db.scalar(
        select(EventFeedback).where(
            EventFeedback.event_id == event_id, EventFeedback.user_id == current_user.id
        )
    )
    if feedback is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="No feedback yet.")
    return feedback


@router.get("/{event_id}/report", response_model=EventReportResponse)
async def get_event_report(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventReportResponse:
    """Post-event report for organizers: attendance plus anonymous feedback summary."""
    event = await get_event_or_404(db, event_id)
    await require_event_manager(db, current_user, event)

    attendance = await attendance_stats(db, event)
    feedback = list(
        (
            await db.scalars(
                select(EventFeedback)
                .where(EventFeedback.event_id == event_id)
                .order_by(EventFeedback.created_at.desc())
            )
        ).all()
    )
    distribution = {rating: 0 for rating in range(1, 6)}
    for item in feedback:
        distribution[item.rating] += 1
    count = len(feedback)
    return EventReportResponse(
        event_id=event.id,
        title=event.title,
        status=event.status.value,
        attendance=attendance,
        feedback_count=count,
        average_rating=round(sum(f.rating for f in feedback) / count, 2) if count else None,
        rating_distribution=distribution,
        feedback_response_rate=(
            round(count / attendance.checked_in, 4) if attendance.checked_in else 0.0
        ),
        comments=[
            FeedbackComment(rating=f.rating, comment=f.comment, created_at=f.created_at)
            for f in feedback
            if f.comment
        ],
    )
