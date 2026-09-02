"""T006 — the base model stamps rows without anyone remembering to.

The mixins are abstract, so there is nothing concrete to save. Each test
declares a throwaway model inside an isolated app registry and creates its
table directly, which keeps the fixture out of the real schema: no migration,
no leftover table in production.
"""

import time
import uuid

import pytest
from django.db import connection, models
from django.test.utils import isolate_apps

from apps.core.models import TimeStampedModel, UUIDMixin


def _create_table(model):
    with connection.schema_editor() as editor:
        editor.create_model(model)


def _drop_table(model):
    with connection.schema_editor() as editor:
        editor.delete_model(model)


@pytest.mark.django_db
@isolate_apps("apps.core")
def test_timestamps_are_filled_in_without_being_passed():
    class Stamped(TimeStampedModel):
        label = models.CharField(max_length=20)

        class Meta:
            app_label = "core"

    _create_table(Stamped)
    try:
        row = Stamped.objects.create(label="first")

        assert row.created_at is not None
        assert row.updated_at is not None
        assert row.created_at.utcoffset().total_seconds() == 0
    finally:
        _drop_table(Stamped)


@pytest.mark.django_db
@isolate_apps("apps.core")
def test_updated_at_moves_on_save_and_created_at_does_not():
    class Stamped(TimeStampedModel):
        label = models.CharField(max_length=20)

        class Meta:
            app_label = "core"

    _create_table(Stamped)
    try:
        row = Stamped.objects.create(label="first")
        created_at, first_update = row.created_at, row.updated_at

        # auto_now reads the clock at save time; without a gap the two stamps
        # can land in the same microsecond and the assertion proves nothing.
        time.sleep(0.01)
        row.label = "second"
        row.save()
        row.refresh_from_db()

        assert row.updated_at > first_update
        assert row.created_at == created_at
    finally:
        _drop_table(Stamped)


@pytest.mark.django_db
@isolate_apps("apps.core")
def test_public_id_is_generated_and_unique():
    class Public(UUIDMixin):
        label = models.CharField(max_length=20)

        class Meta:
            app_label = "core"

    _create_table(Public)
    try:
        first = Public.objects.create(label="a")
        second = Public.objects.create(label="b")

        assert isinstance(first.public_id, uuid.UUID)
        assert first.public_id != second.public_id
    finally:
        _drop_table(Public)
