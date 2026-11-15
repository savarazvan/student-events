from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.models import NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: NotificationType
    title: str
    message: str
    event_id: UUID | None
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class AnnouncementCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    message: Annotated[str, Field(min_length=1, max_length=5000)]

    @field_validator("title", "message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be blank.")
        return value


class AnnouncementResponse(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    message: str
    author_name: str
    created_at: datetime
    recipients: int | None = Field(
        default=None, description="Number of users notified; only returned on creation."
    )
