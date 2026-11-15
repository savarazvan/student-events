"""In-app notifications, e-mail outbox and scheduled event reminders.

Notifications are written in the same transaction as the business change that
causes them (registration, cancellation, ...), so a notification exists if and
only if the change was committed. E-mail delivery is decoupled: a background
job picks up rows with ``emailed_at IS NULL`` (transactional outbox pattern).
Ticket-related e-mails (confirmation, promotion, reminders) carry the QR ticket.
"""

import asyncio
import html
import logging
import os
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    Ticket,
    User,
)
from app.services.tickets import (
    create_ticket_token,
    frontend_url,
    render_qr_png,
    ticket_check_url,
)

logger = logging.getLogger(__name__)

ACTIVE_REGISTRATION_STATUSES = (
    EventRegistrationStatus.CONFIRMED,
    EventRegistrationStatus.WAITLIST,
)
EMAIL_MAX_AGE = timedelta(days=1)
# These e-mails include the attendee's QR ticket when they hold a valid one.
TICKET_EMAIL_TYPES = frozenset(
    {
        NotificationType.REGISTRATION_CONFIRMED.value,
        NotificationType.WAITLIST_PROMOTED.value,
        NotificationType.EVENT_REMINDER.value,
    }
)

EmailSender = Callable[[EmailMessage], None]


def reminder_hours() -> list[int]:
    """Hours before the start at which reminders go out (REMINDER_HOURS, e.g. "24,3")."""
    hours = set()
    for part in os.getenv("REMINDER_HOURS", "24,3").split(","):
        part = part.strip()
        if part.isdigit() and int(part) > 0:
            hours.add(int(part))
    return sorted(hours, reverse=True) or [24, 3]


def _app_timezone() -> timezone | ZoneInfo:
    try:
        return ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Bucharest"))
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def format_when(moment: datetime) -> str:
    """A date and time as people at UBB read it (APP_TIMEZONE, default Europe/Bucharest)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(_app_timezone())
    return f"{local:%d %b %Y, %H:%M} ({local.tzname()})"


def _format_when(event: Event) -> str:
    return format_when(event.start_time)


def _time_left(delta: timedelta) -> str:
    """'in 45 minutes', 'in 1 hour 30 minutes', 'in 22 hours' (minutes rounded to 5)."""
    minutes = max(5, round(delta.total_seconds() / 300) * 5)
    if minutes < 60:
        return f"in {minutes} minutes"
    hours, rest = divmod(minutes, 60)
    if hours >= 6 or rest == 0:
        hours = round(minutes / 60)
        return "in 1 hour" if hours == 1 else f"in {hours} hours"
    return f"in {hours} hour{'s' if hours > 1 else ''} {rest} minutes"


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
    """Create the reminders that are due (default 24h and 3h); safe to run repeatedly.

    A reminder is due once the event starts within its lead time. Only the
    closest reminder is sent (someone registering 1h before the start gets the
    3h reminder, not both). ``dedup_key`` guarantees one reminder of each kind.
    """
    now = now or datetime.now(timezone.utc)
    leads = [timedelta(hours=h) for h in reminder_hours()]
    horizon = now + max(leads)
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
        due = [lead for lead in leads if start - now <= lead]
        if not due:
            continue
        suffix = f"{int(min(due).total_seconds() // 3600)}h"
        label = _time_left(start - now)
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
    """Build an SMTP sender from SMTP_* variables, or None when e-mail is disabled.

    Port 587 uses STARTTLS (SMTP_STARTTLS=true); port 465 uses implicit TLS
    (SMTP_SSL=true, the default for that port).
    """
    host = os.getenv("SMTP_HOST")
    if not host:
        return None
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME") or None
    password = os.getenv("SMTP_PASSWORD") or None
    # Empty SMTP_SSL (as docker-compose passes it) means: decide from the port.
    use_ssl = (os.getenv("SMTP_SSL") or ("true" if port == 465 else "false")).lower() == "true"
    use_starttls = not use_ssl and os.getenv("SMTP_STARTTLS", "false").lower() == "true"
    sender_address = os.getenv("SMTP_FROM") or username or "no-reply@ubb-events.local"

    def send(message: EmailMessage) -> None:
        import smtplib

        if "From" not in message:
            message["From"] = sender_address
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(host, port, timeout=20) as smtp:
            if use_starttls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)

    return send


def build_email(notification: Notification, to: str, ticket: Ticket | None) -> EmailMessage:
    """Plain-text + HTML e-mail for a notification; with the QR ticket when given."""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = notification.title

    text = notification.message
    if ticket is not None:
        text += (
            f"\n\nYour QR ticket is attached. Show it at the entrance."
            f"\nYou can also open it in the app: {frontend_url()}/tickets/{ticket.id}"
        )
    message.set_content(text)
    if ticket is None:
        return message

    qr_cid = make_msgid(domain="ubb-events.local")
    ticket_link = f"{frontend_url()}/tickets/{ticket.id}"
    message.add_alternative(
        f"""<div style="font-family:Segoe UI,Arial,sans-serif;color:#172033;max-width:520px">
  <h2 style="margin:0 0 12px;font-size:20px">{html.escape(notification.title)}</h2>
  <p style="margin:0 0 16px;line-height:1.5">{html.escape(notification.message)}</p>
  <div style="text-align:center;padding:16px;border:1px solid #d7dce8;border-radius:10px">
    <img src="cid:{qr_cid[1:-1]}" alt="QR ticket" width="240" height="240">
    <p style="margin:8px 0 0;font-size:13px;color:#5a6478">Show this QR code at the entrance.</p>
  </div>
  <p style="margin:16px 0 0;font-size:13px;color:#5a6478">
    Open the ticket in the app: <a href="{html.escape(ticket_link)}">{html.escape(ticket_link)}</a>
  </p>
</div>""",
        subtype="html",
    )
    png = render_qr_png(ticket_check_url(create_ticket_token(ticket)))
    message.get_payload()[1].add_related(png, "image", "png", cid=qr_cid, filename="ticket-qr.png")
    return message


async def _valid_ticket(db: AsyncSession, notification: Notification) -> Ticket | None:
    if notification.type not in TICKET_EMAIL_TYPES or notification.event_id is None:
        return None
    return await db.scalar(
        select(Ticket).where(
            Ticket.event_id == notification.event_id,
            Ticket.user_id == notification.user_id,
            Ticket.revoked_at.is_(None),
        )
    )


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
        message = build_email(notification, email, await _valid_ticket(db, notification))
        try:
            # smtplib is blocking; keep the event loop free.
            await asyncio.to_thread(send, message)
        except Exception:  # noqa: BLE001 - keep the row for the next attempt
            logger.exception("Could not e-mail notification %s.", notification.id)
            break
        notification.emailed_at = datetime.now(timezone.utc)
        sent += 1
    await db.commit()
    return sent
