"""Background work on the Odoo boundary.

⚠️ **Nothing here is on a schedule.** These are defined and tested, and adding
any of them to a real beat requires explicit, per-environment permission
(Article 5-2). In v1 scheduling one cron issued 38 unintended invoices, and
the task itself was correct — what was missing was anyone deciding it should
run.

Every task holds a single-instance lock (Article 5-1). No exceptions.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.locks import single_instance
from .models import OutboxMessage, OutboxState
from . import outbox

from .models import InboundMessage, InboundState
from .processing import INTERPRETED_SOURCE, process

log = logging.getLogger(__name__)

#: Give up automatic retries after this many, and leave the message for a
#: person. A message that has failed six times is not failing for a reason
#: another attempt will fix.
MAX_ATTEMPTS = 6

#: Backoff in minutes by attempt number: ~1m, 5m, 25m, 2h, 10h, then daily.
BACKOFF_MINUTES = [1, 5, 25, 125, 625, 1440]


def next_attempt_after(attempts: int) -> timedelta:
    index = min(attempts, len(BACKOFF_MINUTES) - 1)
    return timedelta(minutes=BACKOFF_MINUTES[index])


def due_messages(now=None) -> list[InboundMessage]:
    """Odoo messages that failed, whose backoff has elapsed, with attempts left.

    ``source`` is part of the filter, and it is not decoration. `InboundMessage`
    is shared with the payment gateway, and `failed` there means "we could not
    interpret this body" — the same word, a different sender, and
    `processing.process` reads Odoo's field names. Without this clause the
    retry cron feeds gateway bodies to the Odoo interpreter a minute after they
    arrive, which is exactly the path T913 found: a forged callback needs no
    secret to be *stored*, and storage was enough.

    `processing.process` refuses a foreign source as well. Two guards, because
    this one decides what is *offered* and that one decides what is *acted on*,
    and a queue that keeps offering a forged body is its own problem.
    """
    now = now or timezone.now()
    candidates = InboundMessage.objects.filter(
        source=INTERPRETED_SOURCE,
        state=InboundState.FAILED,
        attempts__lt=MAX_ATTEMPTS,
    ).order_by("received_at")

    due = []
    for message in candidates:
        last = message.processed_at or message.received_at
        if last + next_attempt_after(message.attempts) <= now:
            due.append(message)
    return due


@shared_task(name="odoo.retry_failed")
def retry_failed() -> dict:
    """Re-interpret messages that failed, with backoff.

    Retrying is safe because interpretation is idempotent: the transaction key
    is derived from the payment's identity in Odoo, so a message processed
    twice credits once. What retrying must never do is recreate a charge the
    customer has since been refunded — that guard lives in `processing`, not
    here, so it protects the admin replay button too.
    """
    with single_instance("odoo.retry_failed") as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        results = {"attempted": 0, "processed": 0, "still_failing": 0}
        for message in due_messages():
            results["attempted"] += 1
            process(message)
            if message.state == InboundState.FAILED:
                results["still_failing"] += 1
            else:
                results["processed"] += 1

        log.info("odoo.retry_failed: %s", results)
        return results


@shared_task(name="odoo.abandon_exhausted")
def abandon_exhausted() -> dict:
    """Stop retrying what has run out of attempts, and say so in the note.

    The message stays `failed` — it is not marked `ignored`, because nobody
    decided to ignore it. It leaves the automatic queue and enters the human
    one, and the note is what tells the difference.
    """
    with single_instance("odoo.abandon_exhausted") as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        exhausted = InboundMessage.objects.filter(
            source=INTERPRETED_SOURCE,
            state=InboundState.FAILED,
            attempts__gte=MAX_ATTEMPTS,
        ).exclude(note__contains="تحتاج مراجعة بشرية")

        count = 0
        for message in exhausted:
            message.note = (
                f"{message.note} — تحتاج مراجعة بشرية بعد {message.attempts} محاولات"
            )
            message.save(update_fields=["note"])
            count += 1

        log.info("odoo.abandon_exhausted: flagged %s messages", count)
        return {"flagged": count}


#: كم مرّةً تُعاد محاولةُ رسالةٍ قبل أن تُترك لإنسان. أُسّيّةٌ من دقيقة.
MAX_SEND_ATTEMPTS = 6


@shared_task(name="odoo.send_one", bind=True, max_retries=MAX_SEND_ATTEMPTS)
def send_one(self, message_id: int) -> dict:
    """أرسِل رسالةً واحدة إلى أودو — وأعِد المحاولةَ بتأجيلٍ إن تعذّر.

    **الإدراجُ ينادي الإرسال، والفشلُ ينادي إعادته.** لا استطلاعَ يمرّ على
    الطابور كلَّ دقيقة يسأل «هل فشل شيء؟»: الرسالةُ تعرف متى فشلت، فهي التي
    تحجز محاولتَها التالية.

    والتأجيلُ أُسّيّ (دقيقة، دقيقتان، أربع…) لا ثابت: أودو المتوقّفة لا تُشفى
    بمئة محاولةٍ في الدقيقة، والضغطُ عليها وهي تترنّح يطيل توقّفها.

    و`send` نفسُها تفرّق بين «لم يصل» و«رفضوا»: المرفوضةُ (`ABANDONED`) لا
    تُعاد — إعادةُ إرسالِ ما رُفض تُعطي الجوابَ نفسه وتستهلك محاولة.
    """
    message = OutboxMessage.objects.filter(pk=message_id).first()
    if message is None:
        return {"skipped": f"message {message_id} is gone"}
    if message.state in (OutboxState.CONFIRMED, OutboxState.ABANDONED):
        return {"skipped": f"{message.reference} is {message.state}"}

    result = outbox.send(message)
    if result.state == OutboxState.FAILED:
        # لم نبلغهم — والقاعدةُ أن عدمَ الوصول ليس دليلاً على أن شيئاً لم يقع
        # عندهم (المادة ٢-٤)، فالمرجعُ الفريد يجعل المحاولةَ الثانية آمنة.
        countdown = min(60 * (2**self.request.retries), 3600)
        try:
            self.retry(countdown=countdown)
        except self.MaxRetriesExceededError:
            log.error("odoo: %s exhausted its attempts", message.reference)
            return {"reference": message.reference, "state": "exhausted"}
    return {"reference": message.reference, "state": result.state}


def dispatch(message: OutboxMessage) -> None:
    """احجز إرسالَ رسالةٍ فور إدراجها. يفشل بهدوءٍ بلا وسيط."""
    try:
        send_one.apply_async(args=[message.pk])
    except Exception as exc:  # noqa: BLE001 — وسيطٌ غائب لا يُسقط الإدراج
        log.warning("could not dispatch %s: %s", message.reference, exc)
