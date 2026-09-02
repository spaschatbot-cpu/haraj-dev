"""Outbound messages to customers — SMS, push, and in-app.

Every send is recorded before it is attempted, so "did he get the message?" has
an answer, and a provider outage looks like a queue rather than like silence.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    SMS = "sms", "رسالة نصية"
    PUSH = "push", "إشعار"
    IN_APP = "in_app", "داخل التطبيق"


class DeliveryState(models.TextChoices):
    QUEUED = "queued", "في الطابور"
    SENT = "sent", "أُرسل"
    DELIVERED = "delivered", "وصل"
    FAILED = "failed", "فشل"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications"
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    template = models.CharField(max_length=64)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)

    state = models.CharField(
        max_length=16, choices=DeliveryState.choices, default=DeliveryState.QUEUED
    )
    provider_reference = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["state", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel} → {self.user_id} ({self.state})"


class Device(models.Model):
    """One handset a customer receives push notifications on. T620.

    **The owner is set from the caller's token, never from a request body.** In
    v1 the client sent the account id alongside the push token, so registering
    somebody else's handset was a form field away — and the alerts that go out
    on this channel say what a person is bidding on and for how much.

    The token is unique across the whole table rather than per user, and that is
    the interesting constraint: a handset that changes hands re-registers with
    the *same* provider token under a new account, and without this the previous
    owner would keep receiving the new one's bid alerts. Re-registration moves
    the row instead of adding one.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices"
    )

    #: What the push provider calls this handset. A credential for sending to
    #: it, so it is never returned in a response — see the serializer.
    token = models.CharField(max_length=255, unique=True)

    platform = models.CharField(
        max_length=16,
        choices=[("android", "أندرويد"), ("ios", "آي أو إس"), ("web", "ويب")],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"], name="device_user_recent"),
        ]

    def __str__(self) -> str:
        return f"{self.platform} · {self.user_id}"

    @property
    def token_tail(self) -> str:
        """The last six characters, enough to tell two handsets apart on a screen."""
        return self.token[-6:]
