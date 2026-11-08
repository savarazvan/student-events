from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.models import EventStatus
from app.models.models import EventRegistrationStatus


class EventCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    location: Annotated[str, Field(min_length=1, max_length=255)]
    start_time: datetime
    end_time: datetime
    capacity: Annotated[int, Field(gt=0)]
    organization_id: UUID
    image_url: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Event times must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class EventUpdate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    location: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: Annotated[int, Field(gt=0)] | None = None
    image_url: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event times must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "EventUpdate":
        for field_name in ("title", "location", "start_time", "end_time", "capacity"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class EventStatusUpdate(BaseModel):
    status: EventStatus


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    status: EventStatus
    organization_id: UUID
    created_by_id: UUID
    created_at: datetime
    image_url: str | None


class EventRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    status: EventRegistrationStatus
    registered_at: datetime


class AttendeeResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    registered_at: datetime
    status: EventRegistrationStatus


class PaginatedEventsResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    size: int
