"""Article 5-6, the message half: a non-production message says where it came from.

The banner on a screen covers the interface. These tests cover what leaves the
building — and that is the half v1 got wrong, when a test message reached a real
customer who read it and acted on it.

The decision has one rule with an asymmetric bias, and most of what is below
exists to pin the bias down rather than the happy path: **only an explicitly
production environment sends unstamped.** An environment that is misconfigured,
half-deployed, or named something nobody anticipated stamps, because the cost of
a needless stamp is a line of noise and the cost of a missing one is a customer
acting on a test.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.core.environment import environment_label, is_production, stamp_environment

MESSAGE = "رمز التحقق: 123456"


@pytest.mark.parametrize("name", ["production", "prod", "Production", "  production  "])
def test_production_sends_the_message_untouched(name):
    """A real customer needs no warning, and a permanent one teaches him to ignore it."""
    with override_settings(ENVIRONMENT_NAME=name):
        assert is_production()
        assert stamp_environment(MESSAGE) == MESSAGE


@pytest.mark.parametrize(
    ("name", "label"),
    [("development", "تطوير"), ("test", "اختبار"), ("staging", "تجريب")],
)
def test_every_other_environment_names_itself_in_arabic(name, label):
    with override_settings(ENVIRONMENT_NAME=name):
        assert environment_label() == label
        assert stamp_environment(MESSAGE) == f"[{label}] {MESSAGE}"


def test_the_stamp_is_a_prefix_so_a_lock_screen_preview_carries_it():
    """A trailing warning is missed by the reader who never opened the message.

    Phones show the first characters of an SMS in the notification preview. The
    v1 customer acted on the preview.
    """
    with override_settings(ENVIRONMENT_NAME="staging"):
        assert stamp_environment(MESSAGE).startswith("[تجريب]")


def test_an_environment_nobody_anticipated_still_stamps():
    """Unknown is not production. The default has to fall the safe way."""
    with override_settings(ENVIRONMENT_NAME="qa-2"):
        assert not is_production()
        assert stamp_environment(MESSAGE) == f"[qa-2] {MESSAGE}"


def test_an_unknown_name_is_shown_as_configured_not_replaced():
    """`[qa-2]` tells the holder which box sent this; «بيئة اختبار» tells him nothing."""
    with override_settings(ENVIRONMENT_NAME="qa-2"):
        assert environment_label() == "qa-2"


def test_the_base_sentinel_stamps():
    """`base` means a settings module was pointed at directly — itself the bug.

    An environment that does not know its own name is the last one that should
    be trusted to send unmarked messages.
    """
    with override_settings(ENVIRONMENT_NAME="base"):
        assert stamp_environment(MESSAGE) == "[base] " + MESSAGE


def test_the_code_survives_the_stamp_on_the_first_line():
    """The stamp warns; it must not make the message unusable.

    A customer on staging still has to be able to read his code off the same
    line, and a phone's OTP autofill still has to find it — so the stamp
    contributes no digits of its own.
    """
    with override_settings(ENVIRONMENT_NAME="staging"):
        first_line = stamp_environment(MESSAGE).split("\n")[0]
        assert "".join(ch for ch in first_line if ch.isdigit()) == "123456"
