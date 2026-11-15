from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import EventCategory, EventRegistrationStatus, EventStatus
from app.services.tickets import TicketState


class TicketEventSummary(BaseModel):
    id: UUID
    title: str
    location: str
    start_time: datetime
    end_time: datetime
    status: EventStatus
    category: EventCategory
    organization_id: UUID


class TicketResponse(BaseModel):
    id: UUID
    registration_id: UUID
    state: TicketState
    issued_at: datetime
    checked_in_at: datetime | None
    # Opaque signed value to encode in the QR code (or fetch the ready-made SVG).
    qr_token: str | None = Field(
        description="Only present while the ticket is valid or used; null when revoked."
    )
    event: TicketEventSummary


class MyRegistrationResponse(BaseModel):
    id: UUID
    status: EventRegistrationStatus
    registered_at: datetime
    ticket_id: UUID | None
    ticket_state: TicketState | None
    checked_in_at: datetime | None
    event: TicketEventSummary


class CheckInRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)


class ManualCheckInRequest(BaseModel):
    user_id: UUID


class CheckInResponse(BaseModel):
    ticket_id: UUID
    user_id: UUID
    full_name: str
    email: str
    checked_in_at: datetime
    checked_in_by_id: UUID | None


class AttendanceStatsResponse(BaseModel):
    event_id: UUID
    capacity: int
    confirmed: int
    waitlisted: int
    cancelled: int
    checked_in: int
    not_checked_in: int
    attendance_rate: float = Field(description="checked_in / confirmed, 0 when nobody is confirmed")
    spots_left: int
