from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.ticket import AttendanceStatsResponse


class FeedbackCreate(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5)]
    comment: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("comment")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


class FeedbackComment(BaseModel):
    """Anonymous: organizers see the rating and text, not who wrote it."""

    rating: int
    comment: str
    created_at: datetime


class EventReportResponse(BaseModel):
    event_id: UUID
    title: str
    status: str
    attendance: AttendanceStatsResponse
    feedback_count: int
    average_rating: float | None
    rating_distribution: dict[int, int] = Field(description="rating (1-5) -> number of answers")
    feedback_response_rate: float = Field(description="feedback_count / checked_in")
    comments: list[FeedbackComment]
