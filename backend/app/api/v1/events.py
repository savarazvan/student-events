from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.core.image_utils import validate_image_url
from app.models.models import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    GlobalRole,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)
from app.schemas.event import (
    AttendeeResponse,
    EventCreate,
    EventRegistrationResponse,
    EventResponse,
    EventStatusUpdate,
    EventUpdate,
    PaginatedEventsResponse,
)

router = APIRouter(prefix="/events", tags=["Events"])
EVENT_MANAGER_ROLES: tuple[OrgRole, ...] = (OrgRole.ADMIN, OrgRole.ORGANIZER)
EVENT_NOT_FOUND_DETAIL = "Event not found."


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _require_organization_role(
    db: AsyncSession,
    user: User,
    organization_id: UUID,
    allowed_roles: Sequence[OrgRole],
) -> None:
    organization_exists = await db.scalar(
        select(Organization.id).where(Organization.id == organization_id)
    )
    if organization_exists is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    if user.global_role == GlobalRole.SUPER_ADMIN:
        return

    membership_exists = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.role_in_org.in_(allowed_roles),
        )
    )
    if membership_exists is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization.",
        )


async def _require_event_manager(
    db: AsyncSession,
    user: User,
    event: Event,
    allowed_roles: Sequence[OrgRole],
) -> None:
    if user.global_role == GlobalRole.SUPER_ADMIN:
        return

    membership_exists = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == event.organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.role_in_org.in_(allowed_roles),
        )
    )
    if membership_exists is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this event.",
        )


@router.get("", response_model=PaginatedEventsResponse)
async def list_events(
    organization_id: UUID | None = None,
    event_status: EventStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEventsResponse:
    can_view_all_statuses = current_user is not None and (
        current_user.global_role == GlobalRole.SUPER_ADMIN
    )
    if (
        current_user is not None
        and not can_view_all_statuses
        and organization_id is not None
    ):
        member_id = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role_in_org.in_(EVENT_MANAGER_ROLES),
            )
        )
        can_view_all_statuses = member_id is not None

    filters = []
    if organization_id is not None:
        filters.append(Event.organization_id == organization_id)
    if search is not None:
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Event.title.ilike(search_pattern),
                Event.description.ilike(search_pattern),
            )
        )

    if can_view_all_statuses:
        if event_status is not None:
            filters.append(Event.status == event_status)
    else:
        filters.append(Event.status == EventStatus.PUBLISHED)

    total = await db.scalar(select(func.count()).select_from(Event).where(*filters))
    result = await db.scalars(
        select(Event)
        .where(*filters)
        .order_by(Event.start_time, Event.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return PaginatedEventsResponse(
        items=list(result.all()),
        total=total or 0,
        page=page,
        size=size,
    )


@router.post("", response_model=EventResponse, status_code=http_status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    await _require_organization_role(
        db, current_user, payload.organization_id, EVENT_MANAGER_ROLES
    )
    validate_image_url(payload.image_url)

    event = Event(
        title=payload.title,
        description=payload.description,
        location=payload.location,
        start_time=payload.start_time,
        end_time=payload.end_time,
        capacity=payload.capacity,
        status=EventStatus.DRAFT,
        organization_id=payload.organization_id,
        created_by_id=current_user.id,
        image_url=payload.image_url,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )

    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
    updates = payload.model_dump(exclude_unset=True)
    if "image_url" in updates:
        validate_image_url(updates["image_url"])
    start_time = updates.get("start_time", event.start_time)
    end_time = updates.get("end_time", event.end_time)
    if _as_utc(end_time) <= _as_utc(start_time):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time.",
        )

    for field, value in updates.items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.patch("/{event_id}/status", response_model=EventResponse)
async def update_event_status(
    event_id: UUID,
    payload: EventStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )

    await _require_event_manager(db, current_user, event, (OrgRole.ADMIN,))
    event.status = payload.status
    await db.commit()
    await db.refresh(event)
    return event


@router.post(
    "/{event_id}/register",
    response_model=EventRegistrationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def register_for_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventRegistration:
    event = await db.scalar(
        select(Event).where(Event.id == event_id).with_for_update()
    )
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )

    registration = await db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
        )
    )
    if registration is not None and registration.status != EventRegistrationStatus.CANCELLED:
        return registration

    confirmed_count = await db.scalar(
        select(func.count())
        .select_from(EventRegistration)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status == EventRegistrationStatus.CONFIRMED,
        )
    )
    registration_status = (
        EventRegistrationStatus.CONFIRMED
        if (confirmed_count or 0) < event.capacity
        else EventRegistrationStatus.WAITLIST
    )

    if registration is None:
        registration = EventRegistration(
            event_id=event_id,
            user_id=current_user.id,
            status=registration_status,
        )
        db.add(registration)
    else:
        registration.status = registration_status
        registration.registered_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(registration)
    return registration


@router.delete(
    "/{event_id}/register",
    response_model=EventRegistrationResponse,
)
async def cancel_event_registration(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventRegistration:
    event = await db.scalar(
        select(Event).where(Event.id == event_id).with_for_update()
    )
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )

    registration = await db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
        )
    )
    if registration is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Event registration not found.",
        )
    if registration.status == EventRegistrationStatus.CANCELLED:
        return registration

    was_confirmed = registration.status == EventRegistrationStatus.CONFIRMED
    registration.status = EventRegistrationStatus.CANCELLED
    if was_confirmed:
        next_waitlisted = await db.scalar(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == EventRegistrationStatus.WAITLIST,
            )
            .order_by(EventRegistration.registered_at, EventRegistration.id)
            .limit(1)
            .with_for_update()
        )
        if next_waitlisted is not None:
            next_waitlisted.status = EventRegistrationStatus.CONFIRMED

    await db.commit()
    await db.refresh(registration)
    return registration


@router.get("/{event_id}/attendees", response_model=list[AttendeeResponse])
async def list_event_attendees(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttendeeResponse]:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=EVENT_NOT_FOUND_DETAIL,
        )
    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)

    result = await db.execute(
        select(EventRegistration, User)
        .join(User, User.id == EventRegistration.user_id)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status != EventRegistrationStatus.CANCELLED,
        )
        .order_by(EventRegistration.registered_at, EventRegistration.id)
    )
    return [
        AttendeeResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            registered_at=registration.registered_at,
            status=registration.status,
        )
        for registration, user in result.all()
    ]
