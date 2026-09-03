"""The seam between "we decided to send a code" and "a provider carried it".

One function, resolved from settings, so swapping providers is a settings change
and every path that sends a code keeps sending it the same way. The backend
raises :class:`SmsSendFailed` when the provider refuses or breaks; T603 is what
turns that into a distinct client code and a line on the health screen, and it
has a class to catch because this seam exists first.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils.module_loading import import_string

from apps.core.environment import stamp_environment

log = logging.getLogger(__name__)


class SmsSendFailed(Exception):
    """The provider did not accept the message.

    Deliberately not a DomainError: the customer did nothing wrong, and the
    difference between "your code is wrong" and "we could not send you one" is
    the whole point of T603.
    """

    def __init__(self, message: str = "", *, provider: str = ""):
        self.provider = provider
        super().__init__(message or "sms provider refused the message")


def send_sms(*, phone: str, body: str) -> None:
    """Hand ``body`` to the configured provider for ``phone``.

    The environment stamps itself onto the body **here**, at the seam, rather
    than at each call site (Article 5-6, Article 4-5). A stamp every caller has
    to remember is a stamp that the caller written in a hurry forgets — and
    that is precisely the caller who ships to staging while staging still
    points at a real list of numbers. Passing through this function is the only
    way a message reaches a provider, so passing through it is where the
    guarantee belongs.

    Production is unchanged; see :func:`apps.core.environment.stamp_environment`.
    """
    backend = import_string(settings.SMS_BACKEND)
    backend(phone=phone, body=stamp_environment(body))


def console_backend(*, phone: str, body: str) -> None:
    """Development and CI: log that a message would have gone out.

    The body is logged because in development the code *is* the delivery
    mechanism. Production must not point SMS_BACKEND here — `prod.py` requires a
    real one — or codes would end up in the application log.
    """
    log.info("SMS to %s: %s", phone, body)


def disabled_backend(*, phone: str, body: str) -> None:
    """Refuse to send, loudly, without ever writing the code anywhere.

    The honest stand-in for "no provider is configured here". Unlike the console
    backend it leaks nothing, and unlike an empty setting it fails at the moment
    of sending with a sentence that names the cause — so an environment brought
    up without SMS credentials says so on the first sign-in attempt instead of
    appearing to work.

    This is what CI audits production against: a real, importable backend that
    is not the console one.
    """
    raise SmsSendFailed("no SMS provider is configured for this environment")
