from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.api.event_access import (
    EVENT_MANAGER_ROLES,
    get_event_or_404 as _get_event_or_404,
    get_visible_event,
    is_event_manager as _is_event_manager,
    require_event_manager as _require_event_manager,
)
from app.core.database import get_db
from app.core.image_utils import validate_image_url
from app.models.models import (
    Event,
    EventCategory,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    GlobalRole,
    NotificationType,
    Organization,
    OrganizationMember,
    OrgRole,
    Ticket,
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
from app.schemas.ticket import (
    AttendanceStatsResponse,
    CheckInRequest,
    CheckInResponse,
    ManualCheckInRequest,
)
from app.services.attendance import attendance_stats, check_in_closed_reason
from app.services.event_lifecycle import (
    FINAL_STATUSES,
    is_transition_allowed,
    roles_for_transition,
)
from app.services.registrations import (
    as_utc,
    cancel_registration,
    count_confirmed,
    get_event_for_update,
    promote_waitlist,
    register_user,
    revoke_all_event_tickets,
)
from app.services.notifications import notify_users, registrant_ids
from app.services.tickets import InvalidTicketToken, codes_match, decode_ticket_token

router = APIRouter(prefix="/events", tags=["Events"])
# Statuses listed in the public discovery feed.
DISCOVERABLE_STATUSES: tuple[EventStatus, ...] = (EventStatus.PUBLISHED, EventStatus.IN_PROGRESS)
INVALID_TICKET_DETAIL = "Invalid ticket."


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


@router.get("", response_model=PaginatedEventsResponse)
async def list_events(
    organization_id: UUID | None = None,
    event_status: EventStatus | None = Query(default=None, alias="status"),
    category: EventCategory | None = None,
    starts_after: datetime | None = Query(default=None, description="Inclusive, ISO 8601"),
    starts_before: datetime | None = Query(default=None, description="Exclusive, ISO 8601"),
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
    if category is not None:
        filters.append(Event.category == category)
    if starts_after is not None:
        filters.append(Event.start_time >= as_utc(starts_after))
    if starts_before is not None:
        filters.append(Event.start_time < as_utc(starts_before))
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
    elif event_status in DISCOVERABLE_STATUSES:
        filters.append(Event.status == event_status)
    else:
        filters.append(Event.status.in_(DISCOVERABLE_STATUSES))

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
        category=payload.category,
        registration_deadline=payload.registration_deadline,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    return await get_visible_event(db, event_id, current_user)


# Changes registrants must hear about: field -> label used in the notification.
CRITICAL_FIELDS = {"start_time": "start time", "end_time": "end time", "location": "location"}


def _differs(old: object, new: object) -> bool:
    if isinstance(old, datetime) and isinstance(new, datetime):
        return as_utc(old) != as_utc(new)
    return old != new


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await get_event_for_update(db, event_id)
    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
    if event.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"A {event.status.value} event can no longer be modified.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "image_url" in updates:
        validate_image_url(updates["image_url"])
    start_time = as_utc(updates.get("start_time", event.start_time))
    end_time = as_utc(updates.get("end_time", event.end_time))
    if end_time <= start_time:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time.",
        )
    deadline = updates.get("registration_deadline", event.registration_deadline)
    if deadline is not None and as_utc(deadline) > start_time:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="registration_deadline must not be after start_time.",
        )

    new_capacity = updates.get("capacity", event.capacity)
    confirmed = await count_confirmed(db, event.id)
    if new_capacity < confirmed:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Capacity cannot be lower than the {confirmed} confirmed registrations."
            ),
        )
    capacity_increased = new_capacity > event.capacity
    changed_logistics = [
        label
        for field, label in CRITICAL_FIELDS.items()
        if field in updates and _differs(getattr(event, field), updates[field])
    ]

    for field, value in updates.items():
        setattr(event, field, value)
    await db.flush()
    is_live = event.status in (EventStatus.PUBLISHED, EventStatus.IN_PROGRESS)
    if capacity_increased and is_live:
        await promote_waitlist(db, event)
    if changed_logistics and is_live:
        notify_users(
            db,
            await registrant_ids(db, event.id),
            NotificationType.EVENT_UPDATED,
            f"Event updated: {event.title}",
            f"The {', '.join(changed_logistics)} of {event.title} changed. "
            f"It now takes place on {as_utc(event.start_time):%d %b %Y, %H:%M} UTC "
            f"at {event.location}.",
            event.id,
        )

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
    event = await get_event_for_update(db, event_id)
    current, target = event.status, payload.status
    if current == target:
        await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
        return event
    if not is_transition_allowed(current, target):
        await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Cannot change event status from {current.value} to {target.value}.",
        )
    await _require_event_manager(db, current_user, event, roles_for_transition(current, target))

    if target == EventStatus.PUBLISHED and as_utc(event.end_time) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An event that has already ended cannot be published.",
        )

    event.status = target
    if target == EventStatus.CANCELLED:
        notify_users(
            db,
            await registrant_ids(db, event.id),
            NotificationType.EVENT_CANCELLED,
            f"Event cancelled: {event.title}",
            f"{event.title}, planned for {as_utc(event.start_time):%d %b %Y, %H:%M} UTC, "
            "has been cancelled by the organizers. Your ticket is no longer valid.",
            event.id,
        )
        await revoke_all_event_tickets(db, event.id)
    elif target == EventStatus.COMPLETED:
        attendees = await db.scalars(
            select(Ticket.user_id).where(
                Ticket.event_id == event.id,
                Ticket.revoked_at.is_(None),
                Ticket.checked_in_at.is_not(None),
            )
        )
        notify_users(
            db,
            attendees.all(),
            NotificationType.FEEDBACK_REQUESTED,
            f"How was {event.title}?",
            f"Thanks for attending {event.title}! Rate the event and leave a comment "
            "on its page to help the organizers improve.",
            event.id,
        )
    await db.commit()
    await db.refresh(event)
    return event


async def _registration_response(
    db: AsyncSession, registration: EventRegistration
) -> EventRegistrationResponse:
    ticket = await db.scalar(
        select(Ticket).where(
            Ticket.registration_id == registration.id, Ticket.revoked_at.is_(None)
        )
    )
    response = EventRegistrationResponse.model_validate(registration)
    if ticket is not None:
        response.ticket_id = ticket.id
        response.checked_in_at = ticket.checked_in_at
    return response


@router.get("/{event_id}/register", response_model=EventRegistrationResponse)
async def get_my_event_registration(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventRegistrationResponse:
    """The current user's registration for this event (404 when not registered)."""
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
    return await _registration_response(db, registration)


@router.post(
    "/{event_id}/register",
    response_model=EventRegistrationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def register_for_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventRegistrationResponse:
    registration = await register_user(db, event_id, current_user)
    return await _registration_response(db, registration)


@router.delete(
    "/{event_id}/register",
    response_model=EventRegistrationResponse,
)
async def cancel_event_registration(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventRegistrationResponse:
    registration = await cancel_registration(db, event_id, current_user)
    return await _registration_response(db, registration)


@router.get("/{event_id}/attendees", response_model=list[AttendeeResponse])
async def list_event_attendees(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttendeeResponse]:
    event = await _get_event_or_404(db, event_id)
    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)

    result = await db.execute(
        select(EventRegistration, User, Ticket)
        .join(User, User.id == EventRegistration.user_id)
        .outerjoin(
            Ticket,
            (Ticket.registration_id == EventRegistration.id) & Ticket.revoked_at.is_(None),
        )
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
            ticket_id=ticket.id if ticket else None,
            checked_in_at=ticket.checked_in_at if ticket else None,
        )
        for registration, user, ticket in result.all()
    ]


# --- Check-in -----------------------------------------------------------------


async def _get_event_for_checkin(db: AsyncSession, event_id: UUID, user: User) -> Event:
    event = await _get_event_or_404(db, event_id)
    await _require_event_manager(db, user, event, EVENT_MANAGER_ROLES)
    reason = check_in_closed_reason(event)
    if reason is not None:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=reason)
    return event


async def _complete_check_in(
    db: AsyncSession, ticket: Ticket, scanner: User
) -> CheckInResponse:
    if ticket.revoked_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Ticket has been revoked (registration cancelled).",
        )
    if ticket.checked_in_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Ticket already checked in at {as_utc(ticket.checked_in_at).isoformat()}.",
        )
    ticket.checked_in_at = datetime.now(timezone.utc)
    ticket.checked_in_by_id = scanner.id
    await db.commit()
    await db.refresh(ticket)
    attendee = await db.get(User, ticket.user_id)
    return CheckInResponse(
        ticket_id=ticket.id,
        user_id=attendee.id,
        full_name=attendee.full_name,
        email=attendee.email,
        checked_in_at=ticket.checked_in_at,
        checked_in_by_id=ticket.checked_in_by_id,
    )


@router.post("/{event_id}/check-in", response_model=CheckInResponse)
async def check_in_with_qr(
    event_id: UUID,
    payload: CheckInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckInResponse:
    """Validate a scanned QR ticket token and mark the attendee as checked in."""
    await _get_event_for_checkin(db, event_id, current_user)
    try:
        ticket_id, token_event_id, code = decode_ticket_token(payload.token)
    except InvalidTicketToken:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=INVALID_TICKET_DETAIL
        ) from None
    if token_event_id != event_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="This ticket is for a different event.",
        )

    # Row lock so two scanners cannot check in the same ticket concurrently.
    ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None or ticket.event_id != event_id or not codes_match(ticket.code, code):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=INVALID_TICKET_DETAIL
        )
    return await _complete_check_in(db, ticket, current_user)


@router.post("/{event_id}/check-in/manual", response_model=CheckInResponse)
async def check_in_manually(
    event_id: UUID,
    payload: ManualCheckInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckInResponse:
    """Fallback when a QR code cannot be scanned: check in a confirmed attendee by id."""
    await _get_event_for_checkin(db, event_id, current_user)
    ticket = await db.scalar(
        select(Ticket)
        .where(Ticket.event_id == event_id, Ticket.user_id == payload.user_id)
        .with_for_update()
    )
    if ticket is None or ticket.revoked_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="This user has no valid ticket for the event.",
        )
    return await _complete_check_in(db, ticket, current_user)


@router.delete("/{event_id}/check-in/{ticket_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def undo_check_in(
    event_id: UUID,
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revert a check-in that was made by mistake."""
    event = await _get_event_or_404(db, event_id)
    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
    ticket = await db.scalar(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.event_id == event_id).with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    ticket.checked_in_at = None
    ticket.checked_in_by_id = None
    await db.commit()


@router.get("/{event_id}/attendance", response_model=AttendanceStatsResponse)
async def get_attendance_stats(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttendanceStatsResponse:
    event = await _get_event_or_404(db, event_id)
    await _require_event_manager(db, current_user, event, EVENT_MANAGER_ROLES)
    return await attendance_stats(db, event)
