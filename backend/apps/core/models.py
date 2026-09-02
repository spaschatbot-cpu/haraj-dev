"""Shared base models for every app.

`AuditLog` lands here in T008.
"""

import uuid

from django.db import models


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
