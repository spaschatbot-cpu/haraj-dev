"""What the audit trail must never get wrong.

The second half of this file is the unusual one: it asserts something about the
*shape of the codebase* rather than about a value. That is deliberate — the ban
on signals is the reason the audit trail is trustworthy, and a ban nobody checks
is a preference.
"""

from __future__ import annotations

import ast
import re
import weakref
from decimal import Decimal
from pathlib import Path

import pytest
from django.db.models import signals
from django.db.utils import IntegrityError

from apps.core.audit import record, snapshot
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

BACKEND_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOTS = (BACKEND_ROOT / "apps", BACKEND_ROOT / "config", BACKEND_ROOT / "tests")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000101", full_name="عميل التدقيق", password="x"
    )


@pytest.fixture
def operator(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000102", full_name="موظف", password="x", is_staff=True
    )


class TestRecording:
    def test_it_stores_the_value_before_and_after(self, customer, operator):
        fields = ("full_name",)
        before = snapshot(customer, fields)
        customer.full_name = "الاسم بعد التعديل"
        customer.save(update_fields=["full_name"])
        after = snapshot(customer, fields)

        entry = record(
            action="accounts.rename",
            entity=customer,
            actor=operator,
            before=before,
            after=after,
            note="تصحيح اسم بعد مكالمة دعم",
        )

        stored = AuditLog.objects.get(pk=entry.pk)
        assert stored.before == {"full_name": "عميل التدقيق"}
        assert stored.after == {"full_name": "الاسم بعد التعديل"}
        assert stored.entity_type == "accounts.user"
        assert stored.entity_id == str(customer.pk)
        assert stored.actor_id == operator.pk
        assert stored.note == "تصحيح اسم بعد مكالمة دعم"
        assert stored.at is not None

    def test_a_money_amount_survives_as_text_not_as_a_float(self, customer):
        """Article 3-2: no float touches money, not even on the way to an audit row."""
        entry = record(
            action="money.confiscate",
            entity=customer,
            before={"balance": Decimal("10000.10")},
            after={"balance": Decimal("0.00")},
        )
        stored = AuditLog.objects.get(pk=entry.pk)
        assert stored.before == {"balance": "10000.10"}
        assert stored.after == {"balance": "0.00"}
        assert isinstance(stored.before["balance"], str)

    def test_an_actorless_change_is_allowed_and_says_so(self, customer):
        entry = record(action="money.settle", entity=customer, note="تسوية آلية")
        assert entry.actor_id is None

    def test_the_subject_may_be_named_without_an_instance(self):
        entry = record(
            action="odoo.ignore_message",
            entity_type="odoo.inboundmessage",
            entity_id=4213,
            note="رسالة عن فاتورة غير معروفة",
        )
        assert entry.entity_type == "odoo.inboundmessage"
        assert entry.entity_id == "4213"

    def test_an_entry_without_a_subject_is_refused(self):
        with pytest.raises(ValueError):
            record(action="something.happened")

    def test_the_database_refuses_a_nameless_action(self, customer):
        with pytest.raises(IntegrityError):
            AuditLog.objects.create(
                action="", entity_type="accounts.user", entity_id=str(customer.pk)
            )


class TestAppendOnly:
    def test_an_entry_cannot_be_edited(self, customer):
        entry = record(action="accounts.rename", entity=customer, after={"x": 1})
        entry.note = "غيّرت رأيي"
        with pytest.raises(ValueError):
            entry.save()

    def test_an_entry_cannot_be_deleted(self, customer):
        entry = record(action="accounts.rename", entity=customer)
        with pytest.raises(ValueError):
            entry.delete()


def _project_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*.py")
            if ".venv" not in path.parts and "migrations" not in path.parts
        )
    assert files, "the source scan found no files — the roots must be wrong"
    return files


class TestNoSignals:
    """The audit trail is only believable if nothing writes behind our backs."""

    def test_no_module_connects_a_model_signal(self):
        """A source scan, so a receiver counts even in an app that never loads."""
        # `@receiver(...)`, `post_save.connect(...)`, `signals.post_save.connect(...)`
        connect = re.compile(
            r"(@receiver\b|\b(pre_save|post_save|pre_delete|post_delete|m2m_changed)"
            r"\s*\.\s*connect\b)"
        )
        offenders = []
        for path in _project_python_files():
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            if connect.search(text):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))
        assert offenders == [], (
            "model signals are banned — write the side effect where the decision is "
            f"made (apps.core.audit.record). Found in: {offenders}"
        )

    def test_no_app_config_defines_a_ready_hook_that_imports_signals(self):
        """The usual smuggling route: `def ready(self): from . import signals`."""
        offenders = []
        for path in _project_python_files():
            if path.name != "apps.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "ready":
                    if "signal" in ast.dump(node).lower():
                        offenders.append(str(path.relative_to(BACKEND_ROOT)))
        assert offenders == [], f"AppConfig.ready() must not wire signals: {offenders}"

    def test_nothing_of_ours_is_registered_on_post_save_at_runtime(self):
        """Belt to the source scan's braces: check the live receiver registry.

        Django's own machinery registers here too (contenttypes, auth), so the
        assertion is scoped to receivers that live in our packages.
        """
        ours = []
        for signal in (signals.pre_save, signals.post_save, signals.post_delete):
            for _key, ref in signal.receivers:
                receiver = ref() if isinstance(ref, weakref.ReferenceType) else ref
                if receiver is None:
                    continue
                module = getattr(receiver, "__module__", "") or ""
                if module.startswith(("apps.", "config.")):
                    ours.append(f"{module}.{getattr(receiver, '__name__', receiver)}")
        assert ours == [], f"project code registered model signal receivers: {ours}"
