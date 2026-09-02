"""Recording who changed what.

The whole of the audit trail's API is :func:`record`, and it is called
**explicitly**, from the service layer, on the line that made the decision.

Why not signals
---------------
A ``post_save`` receiver would write these rows for free and would be the wrong
answer. A signal moves the side effect away from the code that caused it, so
the function you are reading no longer tells you what it does; it also fires for
every save — migrations, fixtures, a management shell — and cannot know *why*
the value changed, which is the only part of an audit entry a human needs. v1's
incident reviews spent their time asking "what wrote this?" precisely because
the answer was not at the call site. Here it always is.

`apps/core/tests/test_audit.py` asserts the project registers no ``post_save``
receiver at all, so this stays a rule rather than an intention.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from django.db import models

from .models import AuditLog

__all__ = ["record", "snapshot"]


def _jsonable(value: Any) -> Any:
    """Render one field value in a form JSON can hold without losing it.

    ``Decimal`` becomes a string, never a float: an audit row that says a
    balance was ``10000.000000000001`` is worse than no row, and Article 3-2
    forbids a float anywhere on a money path — an audit trail included.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, models.Model):
        return str(value.pk)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, str | bool | int):
        return value
    return str(value)


def snapshot(
    instance: models.Model, fields: list[str] | tuple[str, ...]
) -> dict[str, Any]:
    """The named fields of ``instance``, in a shape :class:`AuditLog` can store.

    Call it once before the change and once after, with the *same* field list,
    so the two halves of the entry are comparable key by key. Foreign keys are
    read by ``<name>_id`` if you ask for them that way, which avoids a query per
    field just to build an audit row.
    """
    return {name: _jsonable(getattr(instance, name)) for name in fields}


def record(
    *,
    action: str,
    entity: models.Model | None = None,
    entity_type: str = "",
    entity_id: str | int | uuid.UUID = "",
    actor=None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str = "",
    at: dt.datetime | None = None,
) -> AuditLog:
    """Write one audit entry and return it.

    Pass ``entity`` (a saved model instance) and the type and id are read off
    it; pass ``entity_type``/``entity_id`` directly when the subject is already
    gone or is not a model. One of the two is required — an entry that does not
    name its subject is refused by a database CHECK, so failing here just makes
    the message readable.

    ``before`` and ``after`` are dicts, normally built by :func:`snapshot`. They
    are stored as given: this function does not read the database a second time,
    because the caller is the only one who knows which moment "before" means.
    """
    if entity is not None:
        entity_type = entity_type or entity._meta.label_lower
        entity_id = entity_id or entity.pk
    if not entity_type or entity_id in ("", None):
        raise ValueError("record() needs an entity, or an entity_type and entity_id")

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=None if before is None else _jsonable(before),
        after=None if after is None else _jsonable(after),
        note=note,
        **({"at": at} if at is not None else {}),
    )
