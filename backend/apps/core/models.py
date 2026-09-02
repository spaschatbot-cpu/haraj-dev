"""Shared base models for every app.

`TimeStampedModel` and `UUIDMixin` (T006) give every table the same shape.
:class:`AuditLog` (T008) is the one place that answers "who changed this, and
what did it look like before?".
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Adds creation and last-modification stamps to a model.

    Both columns are stored in UTC like everything else; converting for a
    human happens once, at the presentation edge (`apps.core.time`).
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    """Gives a model a stable public identifier.

    The integer primary key stays the internal one. Anything that reaches the
    outside world — a URL, an API response, an Odoo reference — uses this
    instead, so the row count and creation order of a table are never
    inferable from an identifier we hand out.
    """

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """One recorded change to something that matters.

    Written **only** by :func:`apps.core.audit.record`, called explicitly from
    the service layer. There is deliberately no signal receiver behind this
    model: a signal puts the side effect somewhere other than the line that
    decided to make it, and chasing those invisible writes is what made v1's
    incidents so slow to reconstruct. If a change is worth auditing, the code
    that makes it says so out loud.

    Append-only, for the same reason the ledger is: an audit trail that can be
    edited proves nothing about the trail it was meant to protect. ``save`` on
    an existing row and ``delete`` both refuse.
    """

    #: The human who caused the change. NULL means the platform did it by
    #: itself (a cron, a webhook) — which is information, not a missing value.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )

    #: What was done, as a stable dotted name the code owns —
    #: ``money.confiscate``, ``accounts.verify_national_id``. Never a sentence:
    #: reports group by this.
    action = models.CharField(max_length=64)

    #: ``app_label.modelname`` of the subject, and its primary key as text so a
    #: UUID key and an integer key live in one column without a second table.
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)

    #: The subject's relevant fields immediately before and after the change.
    #: Built by :func:`apps.core.audit.snapshot`, which renders Decimals as
    #: strings — a money amount must never pass through a float, not even on
    #: its way into an audit row (Article 3-2).
    before = models.JSONField(null=True, blank=True, default=None)
    after = models.JSONField(null=True, blank=True, default=None)

    #: When the change happened, which the caller may state; it is not always
    #: the moment we got around to writing the row.
    at = models.DateTimeField(default=timezone.now)

    #: Why, in Arabic, for whoever reads this during a dispute.
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            # An entry that does not say what was done, or to what, is noise
            # that still costs a reader time. Refused by the schema so no
            # caller can decide otherwise.
            models.CheckConstraint(condition=~Q(action=""), name="audit_action_is_named"),
            models.CheckConstraint(
                condition=~Q(entity_type="") & ~Q(entity_id=""),
                name="audit_entity_is_named",
            ),
        ]
        indexes = [
            # "What happened to this invoice?" — the question actually asked.
            models.Index(fields=["entity_type", "entity_id", "-at"]),
            models.Index(fields=["actor", "-at"]),
            models.Index(fields=["action", "-at"]),
        ]
        ordering = ["-at", "-id"]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id} at {self.at}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("سجل التدقيق لا يُعدَّل بعد كتابته")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("سجل التدقيق لا يُحذف")
