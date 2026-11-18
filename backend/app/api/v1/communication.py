"""Organizer -> participant communication: event announcements."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.api.event_access import PUBLIC_STATUSES, get_visible_event, require_event_manager
from app.core.database import get_db
from app.models.models import EventAnnouncement, NotificationType, User
from app.schemas.notification import AnnouncementCreate, AnnouncementResponse
from app.services.notifications import notify_users, registrant_ids

router = APIRouter(prefix="/events", tags=["Communication"])


@router.get("/{event_id}/announcements", response_model=list[AnnouncementResponse])
async def list_announcements(
    event_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnouncementResponse]:
    """Announcements are visible to everyone who can see the event, newest first."""
    await get_visible_event(db, event_id, current_user)
    rows = (
        await db.execute(
            select(EventAnnouncement, User.full_name)
            .join(User, User.id == EventAnnouncement.author_id)
            .where(EventAnnouncement.event_id == event_id)
            .order_by(EventAnnouncement.created_at.desc(), EventAnnouncement.id)
        )
    ).all()
    return [
        AnnouncementResponse(
            id=announcement.id,
            event_id=announcement.event_id,
            title=announcement.title,
            message=announcement.message,
            author_name=author_name,
            created_at=announcement.created_at,
        )
        for announcement, author_name in rows
    ]


@router.post(
    "/{event_id}/announcements",
    response_model=AnnouncementResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_announcement(
    event_id: UUID,
    payload: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementResponse:
    """Post an announcement and notify every confirmed or waitlisted registrant."""
    event = await get_visible_event(db, event_id, current_user)
    await require_event_manager(db, current_user, event)
    if event.status not in PUBLIC_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Announcements can only be sent once the event is published.",
        )

    announcement = EventAnnouncement(
        event_id=event.id,
        author_id=current_user.id,
        title=payload.title,
        message=payload.message,
    )
    db.add(announcement)
    recipients = notify_users(
        db,
        await registrant_ids(db, event.id),
        NotificationType.EVENT_ANNOUNCEMENT,
        f"{event.title}: {payload.title}",
        payload.message,
        event.id,
    )
    await db.commit()
    await db.refresh(announcement)
    return AnnouncementResponse(
        id=announcement.id,
        event_id=announcement.event_id,
        title=announcement.title,
        message=announcement.message,
        author_name=current_user.full_name,
        created_at=announcement.created_at,
        recipients=recipients,
    )
