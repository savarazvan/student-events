"""Event organizing team: responsibilities (tasks) assigned to organization members.

Organizers and organization admins plan the work; any member of the organizing
organization can see the team board, and an assignee can update the status of
their own task. This is what gives the ``MEMBER`` role a purpose.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.event_access import (
    ORG_MEMBER_ROLES,
    get_event_or_404,
    has_org_role,
    is_event_manager,
)
from app.core.database import get_db
from app.models.models import (
    Event,
    EventTask,
    NotificationType,
    OrganizationMember,
    User,
)
from app.schemas.task import EventTaskCreate, EventTaskResponse, EventTaskUpdate
from app.services.event_lifecycle import FINAL_STATUSES
from app.services.notifications import add_notification

router = APIRouter(prefix="/events", tags=["Event team"])

TASK_NOT_FOUND_DETAIL = "Task not found."


async def task_response(db: AsyncSession, task: EventTask) -> EventTaskResponse:
    assignee_name = None
    if task.assignee_id is not None:
        assignee_name = await db.scalar(select(User.full_name).where(User.id == task.assignee_id))
    return EventTaskResponse(
        id=task.id,
        event_id=task.event_id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee_id,
        assignee_name=assignee_name,
        status=task.status,
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _require_team_member(db: AsyncSession, user: User, event: Event) -> None:
    if not await has_org_role(db, user, event.organization_id, ORG_MEMBER_ROLES):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only members of the organizing organization can see the event team.",
        )


async def _validate_assignee(db: AsyncSession, event: Event, assignee_id: UUID | None) -> None:
    if assignee_id is None:
        return
    is_member = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == event.organization_id,
            OrganizationMember.user_id == assignee_id,
        )
    )
    if is_member is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tasks can only be assigned to members of the organizing organization.",
        )


def _notify_assignee(db: AsyncSession, task: EventTask, event: Event, assigner: User) -> None:
    if task.assignee_id is None or task.assignee_id == assigner.id:
        return
    add_notification(
        db,
        task.assignee_id,
        NotificationType.TASK_ASSIGNED,
        f"New task for {event.title}",
        f"{assigner.full_name} assigned you \"{task.title}\" for {event.title}.",
        event.id,
    )


async def _get_task_or_404(db: AsyncSession, event_id: UUID, task_id: UUID) -> EventTask:
    task = await db.scalar(
        select(EventTask).where(EventTask.id == task_id, EventTask.event_id == event_id)
    )
    if task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)
    return task


@router.get("/{event_id}/tasks", response_model=list[EventTaskResponse])
async def list_tasks(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventTaskResponse]:
    event = await get_event_or_404(db, event_id)
    await _require_team_member(db, current_user, event)
    tasks = (
        await db.scalars(
            select(EventTask)
            .where(EventTask.event_id == event_id)
            .order_by(EventTask.due_at.is_(None), EventTask.due_at, EventTask.created_at)
        )
    ).all()
    return [await task_response(db, task) for task in tasks]


@router.post(
    "/{event_id}/tasks",
    response_model=EventTaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_task(
    event_id: UUID,
    payload: EventTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventTaskResponse:
    event = await get_event_or_404(db, event_id)
    if not await is_event_manager(db, current_user, event):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only organizers and organization admins can plan tasks.",
        )
    if event.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Tasks cannot be added to a {event.status.value} event.",
        )
    await _validate_assignee(db, event, payload.assignee_id)

    task = EventTask(
        event_id=event.id,
        title=payload.title.strip(),
        description=payload.description,
        assignee_id=payload.assignee_id,
        due_at=payload.due_at,
        created_by_id=current_user.id,
    )
    db.add(task)
    _notify_assignee(db, task, event, current_user)
    await db.commit()
    await db.refresh(task)
    return await task_response(db, task)


@router.patch("/{event_id}/tasks/{task_id}", response_model=EventTaskResponse)
async def update_task(
    event_id: UUID,
    task_id: UUID,
    payload: EventTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventTaskResponse:
    """Managers may change anything; the assignee may only update the status."""
    event = await get_event_or_404(db, event_id)
    task = await _get_task_or_404(db, event_id, task_id)
    updates = payload.model_dump(exclude_unset=True)

    if not await is_event_manager(db, current_user, event):
        if task.assignee_id != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you.",
            )
        if set(updates) - {"status"}:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Assignees can only change the status of their task.",
            )

    reassigned = "assignee_id" in updates and updates["assignee_id"] != task.assignee_id
    if reassigned:
        await _validate_assignee(db, event, updates["assignee_id"])
    for field, value in updates.items():
        setattr(task, field, value.strip() if field == "title" else value)
    task.updated_at = datetime.now(timezone.utc)
    if reassigned:
        _notify_assignee(db, task, event, current_user)
    await db.commit()
    await db.refresh(task)
    return await task_response(db, task)


@router.delete(
    "/{event_id}/tasks/{task_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_task(
    event_id: UUID,
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    event = await get_event_or_404(db, event_id)
    if not await is_event_manager(db, current_user, event):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only organizers and organization admins can delete tasks.",
        )
    task = await _get_task_or_404(db, event_id, task_id)
    await db.delete(task)
    await db.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
