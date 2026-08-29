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
