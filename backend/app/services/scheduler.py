"""Periodic background jobs: event reminders and e-mail outbox delivery.

Runs inside the API process (started from the FastAPI lifespan). Both jobs are
idempotent, so running several API replicas only costs duplicate queries, never
duplicate reminders or e-mails (dedup keys and SKIP LOCKED).
"""

import asyncio
import logging
import os

from app.core.database import AsyncSessionLocal
from app.services.notifications import (
    deliver_pending_emails,
    send_due_reminders,
    smtp_sender_from_env,
)

logger = logging.getLogger(__name__)


def jobs_enabled() -> bool:
    return os.getenv("BACKGROUND_JOBS_ENABLED", "true").lower() == "true"


async def run_jobs_once() -> None:
    async with AsyncSessionLocal() as db:
        reminders = await send_due_reminders(db)
        if reminders:
            logger.info("Created %d event reminders.", reminders)
    sender = smtp_sender_from_env()
    if sender is not None:
        async with AsyncSessionLocal() as db:
            sent = await deliver_pending_emails(db, sender)
            if sent:
                logger.info("Sent %d notification e-mails.", sent)


async def run_scheduler(stop: asyncio.Event) -> None:
    interval = int(os.getenv("JOBS_INTERVAL_SECONDS", "60"))
    while not stop.is_set():
        try:
            await run_jobs_once()
        except Exception:  # noqa: BLE001 - a failed run must not stop the scheduler
            logger.exception("Background jobs failed.")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
