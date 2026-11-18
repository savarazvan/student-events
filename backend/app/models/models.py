from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

_DELETE_ORPHAN_CASCADE = "all, delete-orphan"
_USER_FOREIGN_KEY = "users.id"


class GlobalRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    USER = "USER"


class OrgRole(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    ADMIN = "ORG_ADMIN"
    ORGANIZER = "ORGANIZER"
    MEMBER = "MEMBER"


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EventCategory(str, Enum):
    WORKSHOP = "WORKSHOP"
    CONFERENCE = "CONFERENCE"
    TRAINING = "TRAINING"
    SOCIAL = "SOCIAL"
    VOLUNTEERING = "VOLUNTEERING"
    COMPETITION = "COMPETITION"
    OTHER = "OTHER"


class EventRegistrationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    WAITLIST = "WAITLIST"
    CANCELLED = "CANCELLED"


class EventTaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class NotificationType(str, Enum):
    REGISTRATION_CONFIRMED = "REGISTRATION_CONFIRMED"
    REGISTRATION_WAITLISTED = "REGISTRATION_WAITLISTED"
    WAITLIST_PROMOTED = "WAITLIST_PROMOTED"
    EVENT_UPDATED = "EVENT_UPDATED"
    EVENT_CANCELLED = "EVENT_CANCELLED"
    EVENT_ANNOUNCEMENT = "EVENT_ANNOUNCEMENT"
    EVENT_REMINDER = "EVENT_REMINDER"
    FEEDBACK_REQUESTED = "FEEDBACK_REQUESTED"
    TASK_ASSIGNED = "TASK_ASSIGNED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    global_role: Mapped[GlobalRole] = mapped_column(
        SqlEnum(GlobalRole, name="global_role"), default=GlobalRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization_memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="user", cascade=_DELETE_ORPHAN_CASCADE
    )
    registrations: Mapped[list[EventRegistration]] = relationship(
        back_populates="user", cascade=_DELETE_ORPHAN_CASCADE
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="organization", cascade=_DELETE_ORPHAN_CASCADE
    )
    events: Mapped[list[Event]] = relationship(back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_organization_members_user_org"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    role_in_org: Mapped[OrgRole] = mapped_column(
        SqlEnum(OrgRole, name="org_role"), default=OrgRole.ORGANIZER, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="organization_memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(EventStatus, name="event_status"), default=EventStatus.DRAFT, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[EventCategory] = mapped_column(
        SqlEnum(EventCategory, name="event_category"),
        default=EventCategory.OTHER,
        server_default=EventCategory.OTHER.value,
        nullable=False,
    )
    # Registrations close at this moment; when NULL they close at start_time.
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped[Organization] = relationship(back_populates="events")
    created_by: Mapped[User] = relationship()
    registrations: Mapped[list[EventRegistration]] = relationship(
        back_populates="event", cascade=_DELETE_ORPHAN_CASCADE
    )


class EventRegistration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_registrations_event_user"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), index=True, nullable=False)
    status: Mapped[EventRegistrationStatus] = mapped_column(
        SqlEnum(EventRegistrationStatus, name="event_registration_status"),
        default=EventRegistrationStatus.CONFIRMED,
        nullable=False,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="registrations")
    event: Mapped[Event] = relationship(back_populates="registrations")
    ticket: Mapped[Ticket | None] = relationship(
        back_populates="registration", cascade=_DELETE_ORPHAN_CASCADE, uselist=False
    )


Registration = EventRegistration


class Ticket(Base):
    """Digital entry ticket, issued for a CONFIRMED registration.

    One ticket per registration. ``code`` is random and is rotated whenever the
    ticket is re-issued, so QR tokens of a revoked ticket can never be reused.
    """

    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    registration_id: Mapped[UUID] = mapped_column(
        ForeignKey("registrations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(_USER_FOREIGN_KEY), nullable=True
    )

    registration: Mapped[EventRegistration] = relationship(back_populates="ticket")


class Notification(Base):
    """In-app notification; also the outbox for e-mail delivery (``emailed_at``).

    ``type`` is stored as a plain string (validated by ``NotificationType``) so new
    notification kinds do not need a PostgreSQL enum migration. ``dedup_key``
    makes scheduled notifications such as reminders idempotent.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), index=True, nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("events.id"), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EventAnnouncement(Base):
    """Message an organizer sends to everyone registered for an event."""

    __tablename__ = "event_announcements"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EventFeedback(Base):
    """Post-event rating left by an attendee who checked in."""

    __tablename__ = "event_feedback"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_feedback_event_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_event_feedback_rating"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EventTask(Base):
    """A responsibility within an event's organizing team (e.g. check-in desk)."""

    __tablename__ = "event_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(_USER_FOREIGN_KEY), index=True, nullable=True
    )
    status: Mapped[EventTaskStatus] = mapped_column(
        SqlEnum(EventTaskStatus, name="event_task_status"),
        default=EventTaskStatus.TODO,
        nullable=False,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey(_USER_FOREIGN_KEY), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

