"""In-app notifications, e-mail outbox and scheduled event reminders.

Notifications are written in the same transaction as the business change that
causes them (registration, cancellation, ...), so a notification exists if and
only if the change was committed. E-mail delivery is decoupled: a background
job picks up rows with ``emailed_at IS NULL`` (transactional outbox pattern).
"""

import asyncio
import logging
import os
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    Notification,
    NotificationType,
    User,
)

logger = logging.getLogger(__name__)

ACTIVE_REGISTRATION_STATUSES = (
    EventRegistrationStatus.CONFIRMED,
    EventRegistrationStatus.WAITLIST,
)
# (dedup suffix, how long before the start the reminder is due, label)
REMINDERS: tuple[tuple[str, timedelta, str], ...] = (
    ("24h", timedelta(hours=24), "tomorrow"),
    ("2h", timedelta(hours=2), "in 2 hours"),
)

EMAIL_MAX_AGE = timedelta(days=1)

EmailSender = Callable[[str, str, str], None]


def _format_when(event: Event) -> str:
    start = event.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def add_notification(
    db: AsyncSession,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    event_id: UUID | None = None,
    dedup_key: str | None = None,
) -> Notification:
    """Stage a notification in the current transaction (the caller commits)."""
    notification = Notification(
        user_id=user_id,
        event_id=event_id,
        type=notification_type.value,
        title=title,
        message=message,
        dedup_key=dedup_key,
    )
    db.add(notification)
    return notification


async def registrant_ids(
    db: AsyncSession,
    event_id: UUID,
    statuses: Sequence[EventRegistrationStatus] = ACTIVE_REGISTRATION_STATUSES,
) -> list[UUID]:
    return list(
        (
            await db.scalars(
                select(EventRegistration.user_id).where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status.in_(statuses),
                )
            )
        ).all()
    )


def notify_users(
    db: AsyncSession,
    user_ids: Iterable[UUID],
    notification_type: NotificationType,
    title: str,
    message: str,
    event_id: UUID | None = None,
) -> int:
    count = 0
    for user_id in user_ids:
        add_notification(db, user_id, notification_type, title, message, event_id)
        count += 1
    return count


# --- Messages for registration events ------------------------------------------


def notify_registration(db: AsyncSession, registration: EventRegistration, event: Event) -> None:
    if registration.status == EventRegistrationStatus.CONFIRMED:
        add_notification(
            db,
            registration.user_id,
            NotificationType.REGISTRATION_CONFIRMED,
            f"You're registered: {event.title}",
            f"Your seat is confirmed for {event.title} on {_format_when(event)} at "
            f"{event.location}. Your ticket is in My Schedule.",
            event.id,
        )
    elif registration.status == EventRegistrationStatus.WAITLIST:
        add_notification(
            db,
            registration.user_id,
            NotificationType.REGISTRATION_WAITLISTED,
            f"You're on the waitlist: {event.title}",
            f"{event.title} is full. You are on the waitlist and will get a ticket "
            "automatically if a seat frees up.",
            event.id,
        )


def notify_promoted(db: AsyncSession, registration: EventRegistration, event: Event) -> None:
    add_notification(
        db,
        registration.user_id,
        NotificationType.WAITLIST_PROMOTED,
        f"A seat freed up: {event.title}",
        f"Good news! You moved from the waitlist to confirmed for {event.title} on "
        f"{_format_when(event)}. Your ticket is in My Schedule.",
        event.id,
    )


# --- Scheduled reminders -------------------------------------------------------


async def send_due_reminders(db: AsyncSession, now: datetime | None = None) -> int:
    """Create the 24h / 2h reminders that are due; safe to run repeatedly.

    A reminder is due once the event starts within its lead time. Only the
    closest reminder is sent (someone registering 1h before the start gets the
    2h reminder, not both). ``dedup_key`` guarantees one reminder of each kind.
    """
    now = now or datetime.now(timezone.utc)
    horizon = now + max(lead for _, lead, _ in REMINDERS)
    events = (
        await db.scalars(
            select(Event).where(
                Event.status == EventStatus.PUBLISHED,
                Event.start_time > now,
                Event.start_time <= horizon,
            )
        )
    ).all()

    created = 0
    for event in events:
        start = event.start_time if event.start_time.tzinfo else event.start_time.replace(
            tzinfo=timezone.utc
        )
        due = [r for r in REMINDERS if start - now <= r[1]]
        if not due:
            continue
        suffix, _, label = min(due, key=lambda r: r[1])
        confirmed = await registrant_ids(db, event.id, (EventRegistrationStatus.CONFIRMED,))
        if not confirmed:
            continue
        existing = set(
            (
                await db.scalars(
                    select(Notification.user_id).where(
                        Notification.event_id == event.id,
                        Notification.dedup_key == f"reminder:{suffix}:{event.id}",
                    )
                )
            ).all()
        )
        for user_id in confirmed:
            if user_id in existing:
                continue
            add_notification(
                db,
                user_id,
                NotificationType.EVENT_REMINDER,
                f"Reminder: {event.title} starts {label}",
                f"{event.title} starts on {_format_when(event)} at {event.location}. "
                "Have your QR ticket ready at the entrance.",
                event.id,
                dedup_key=f"reminder:{suffix}:{event.id}",
            )
            created += 1
    try:
        await db.commit()
    except IntegrityError:
        # Another worker created the same reminders concurrently.
        await db.rollback()
        return 0
    return created


# --- E-mail outbox -------------------------------------------------------------


def smtp_sender_from_env() -> EmailSender | None:
    """Build an SMTP sender from SMTP_* variables, or None when e-mail is disabled."""
    host = os.getenv("SMTP_HOST")
    if not host:
        return None
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME") or None
    password = os.getenv("SMTP_PASSWORD") or None
    use_tls = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
    sender_address = os.getenv("SMTP_FROM", "UBB Student Events <no-reply@ubb-events.local>")

    def send(to: str, subject: str, body: str) -> None:
        import smtplib
        from email.message import EmailMessage

        message = EmailMessage()
        message["From"] = sender_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)

    return send


async def deliver_pending_emails(
    db: AsyncSession, send: EmailSender, batch_size: int = 50
) -> int:
    """Send e-mails for notifications not yet e-mailed. Returns how many were sent.

    Only recent notifications are considered, so enabling SMTP later does not
    flood users with old messages.
    """
    cutoff = datetime.now(timezone.utc) - EMAIL_MAX_AGE
    rows = (
        await db.execute(
            select(Notification, User.email)
            .join(User, User.id == Notification.user_id)
            .where(Notification.emailed_at.is_(None), Notification.created_at >= cutoff)
            .order_by(Notification.created_at)
            .limit(batch_size)
            .with_for_update(of=Notification, skip_locked=True)
        )
    ).all()
    sent = 0
    for notification, email in rows:
        try:
            # smtplib is blocking; keep the event loop free.
            await asyncio.to_thread(send, email, notification.title, notification.message)
        except Exception:  # noqa: BLE001 - keep the row for the next attempt
            logger.exception("Could not e-mail notification %s.", notification.id)
            break
        notification.emailed_at = datetime.now(timezone.utc)
        sent += 1
    await db.commit()
    return sent
