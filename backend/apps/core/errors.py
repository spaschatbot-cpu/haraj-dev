"""The one shape every refusal takes.

A refused business operation is not a crash. It is an answer, and the customer
is entitled to read it. :class:`DomainError` is that answer: a stable ``code``
the app switches on, an Arabic ``user_message`` ready to put on a screen, and a
``detail`` map carrying the numbers the message talks about.

The translation from this class to an HTTP response happens in exactly one
place — :mod:`apps.core.exceptions` — so no view, serializer or service ever
formats an error body of its own.
"""

from __future__ import annotations


class DomainError(Exception):
    """A refused operation, expected by the design and safe to show a customer.

    Subclasses set :attr:`code` and :attr:`default_message`. The developer text
    passed positionally stays in English for the logs; ``user_message`` is what
    reaches the screen.
    """

    #: Stable identifier the client branches on. Never translated.
    code = "domain_error"

    #: Shown to the customer when the raiser does not supply a better sentence.
    default_message = "تعذّر تنفيذ العملية."

    def __init__(
        self,
        message: str = "",
        *,
        user_message: str | None = None,
        detail: dict | None = None,
    ):
        self.user_message = user_message or self.default_message
        self.detail = detail or {}
        super().__init__(message or self.user_message)
