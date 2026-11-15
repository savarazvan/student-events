from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.models import EventTaskStatus
from app.schemas.ticket import TicketEventSummary


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("due_at must include a timezone.")
    return value


class EventTaskCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=5000)] | None = None
    assignee_id: UUID | None = None
    due_at: datetime | None = None

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)


class EventTaskUpdate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: Annotated[str, Field(max_length=5000)] | None = None
    assignee_id: UUID | None = None
    due_at: datetime | None = None
    status: EventTaskStatus | None = None

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "EventTaskUpdate":
        for field_name in ("title", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class EventTaskResponse(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    description: str | None
    assignee_id: UUID | None
    assignee_name: str | None
    status: EventTaskStatus
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MyTaskResponse(EventTaskResponse):
    event: TicketEventSummary
