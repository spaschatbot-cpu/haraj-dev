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

    #: 409 by default: a refusal is an answer, and the caller can do something
    #: about it. A subclass overrides this only when that sentence stops being
    #: true — a third party being down is not the caller's request being
    #: refused, and telling the client 409 for it invites the app to give up
    #: rather than retry. `apps.core.exceptions` reads this and nothing else
    #: decides the status of a domain refusal.
    status_code = 409

    def __init__(
        self,
        message: str = "",
        *,
        user_message: str | None = None,
        detail: dict | None = None,
    ):
        self.user_message = user_message or self.default_message

        #: Whether *this raise* supplied the sentence, as opposed to inheriting
        #: the class default. Only the raiser can name this customer's numbers
        #: ("10000.00 مقفولة على مستحقات"), so a sentence it wrote outranks the
        #: wording table in `apps.core.exceptions`; a class default does not.
        self.explicit_message = user_message or ""

        self.detail = detail or {}
        super().__init__(message or self.user_message)
