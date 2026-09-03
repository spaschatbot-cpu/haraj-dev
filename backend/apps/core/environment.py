"""Which environment this is, in a word the person reading the message knows.

Article 5-6 has two halves. The interface half is answered by a banner on the
screen. This module answers the other half — **every message a non-production
environment sends carries its name** — and that is the half that burned v1: a
test message reached a real customer, who read it and acted on it.

A banner cannot help there. An SMS arrives on a lock screen with no interface
around it, and a push notification arrives with the app closed. Whatever warns
the reader has to be *inside the message*, because the message is all he gets.

The mobile app makes the same promise for what it renders
(`mobile/lib/presentation/common/environment_stamp.dart`) and uses the same
``[البيئة] الرسالة`` shape, so a tester who receives a stamped SMS and a
stamped in-app notice recognises them as one warning rather than two
conventions.
"""

from __future__ import annotations

from django.conf import settings

#: The only names that mean "real customers are on the other end of this".
#: Everything else is stamped — :func:`stamp_environment` says why the bias
#: runs this way.
PRODUCTION_NAMES = frozenset({"production", "prod"})

#: Arabic for the environments we run. One definition, because a name written
#: twice drifts, and a tester who reads «تجريب» on the app banner and
#: «staging» in an SMS has been shown two environments that are one
#: (Article 4-5).
ARABIC_NAMES = {
    "development": "تطوير",
    "test": "اختبار",
    "staging": "تجريب",
}


def is_production() -> bool:
    """Whether this environment is the one with real customers on it."""
    return settings.ENVIRONMENT_NAME.strip().lower() in PRODUCTION_NAMES


def environment_label() -> str:
    """The environment's name as a reader should see it.

    An unrecognised name is returned as it was configured rather than replaced
    with something generic: ``[qa-2]`` still tells whoever is holding the phone
    which box sent this, and «بيئة اختبار» tells him nothing he can act on.
    """
    raw = settings.ENVIRONMENT_NAME.strip()
    return ARABIC_NAMES.get(raw.lower(), raw)


def stamp_environment(message: str) -> str:
    """``message``, carrying this environment's name unless this is production.

    **The bias is deliberate: anything not explicitly production gets stamped.**
    The two ways to be wrong are not equal. An unstamped test message is the v1
    incident — a customer treats it as real. A stamped production message is a
    line of noise in front of a code that still works. So a misconfigured
    environment, one still on the ``base`` sentinel, and one named something
    this module has never seen all stamp.

    Production is unstamped because a real customer needs no warning, and a
    permanent one would only teach him to ignore the next one.

    The stamp is a **prefix**, not a trailing line: a phone shows the first
    characters of an SMS in its notification preview, and a warning that only
    appears once the message is opened is missed by exactly the reader who
    acted without opening it.
    """
    if is_production():
        return message
    return f"[{environment_label()}] {message}"
