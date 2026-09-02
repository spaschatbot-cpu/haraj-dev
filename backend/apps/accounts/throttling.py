"""How often one caller may make us send an SMS.

The per-code limits already in :mod:`apps.accounts.services` are properties of a
*code*: five guesses against this code, no second code while this one is young.
They cap what an attacker gets out of a code he already caused to be sent. They
do not cap how many he causes to be sent, and that is the meter that costs money
— every send is a paid message whether or not anybody ever types it.

Two limits, and each covers the hole the other leaves
-----------------------------------------------------
* **Per phone number.** One number cannot be made to ring all afternoon. The
  resend cooldown in `send_verification_code` already refuses a second message
  while the first is live, but it expires with the code: a caller who waits out
  the cooldown can request a fresh message every minute forever, which is a
  harassment tool pointed at whoever owns the number.
* **Per caller address.** The per-phone limit alone is defeated by walking the
  numbering plan — one request each for a thousand different numbers costs a
  thousand messages and trips no per-number limit anywhere. That was the shape
  of the bill nobody could explain in v1.

Neither is redundant. A limit on the number alone lets one attacker burn the
budget across many numbers; a limit on the address alone lets a botnet aim every
one of its addresses at a single victim's phone.

Why the rates are not DRF's ``DEFAULT_THROTTLE_RATES``
-----------------------------------------------------
`settings/test.py` empties DRF's throttle configuration on purpose: a suite in
which every test silently consumes a shared counter is a suite whose results
depend on the order it ran in. These classes therefore read their own
:data:`~django.conf.settings.OTP_THROTTLE_RATES`, and a scope missing from that
dict means *this limit is off here* rather than an ImproperlyConfigured at the
first request. So the tests that prove the limits work switch them on explicitly
with ``override_settings`` and nothing else in the suite is metered at all.

"Off by default" is only safe because it is loud: `apps.accounts.checks` refuses
a deployed environment whose rates are missing, and refuses one whose cache is
per-process — see there for why a local-memory cache makes a limit a lie.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class _OtpThrottle(SimpleRateThrottle):
    """Shared plumbing: the rate comes from our own settings dict, or is off.

    ``SimpleRateThrottle`` already treats ``rate is None`` as "allow", so
    returning ``None`` here is the whole of the off switch — there is no second
    branch anywhere that has to remember to check whether throttling is enabled.
    """

    def get_rate(self) -> str | None:
        rates: dict[str, str] = getattr(settings, "OTP_THROTTLE_RATES", {})
        return rates.get(self.scope)

    def _key(self, ident: str) -> str:
        """DRF's own cache-key shape, kept rather than reinvented.

        ``str()`` because ``cache_format`` is untyped upstream and a key that is
        `Any` spreads that through every caller.
        """
        return str(self.cache_format % {"scope": self.scope, "ident": ident})


class OtpSendPerPhoneThrottle(_OtpThrottle):
    """How many codes one *number* may be sent, whoever asks for them."""

    scope = "otp_send_phone"

    def get_cache_key(self, request, view) -> str | None:
        phone = _requested_phone(request)
        if not phone:
            # No number in the body means the serializer is about to refuse the
            # request anyway. Metering it would let a caller spend somebody
            # else's budget — or a shared `None` bucket — by sending rubbish.
            return None
        return self._key(phone)


class OtpSendPerCallerThrottle(_OtpThrottle):
    """How many codes one *address* may cause to be sent, to any numbers."""

    scope = "otp_send_caller"

    def get_cache_key(self, request, view) -> str | None:
        return self._key(self.get_ident(request))


class OtpVerifyPerCallerThrottle(_OtpThrottle):
    """How many codes one address may *try*, across all numbers.

    The five-guess budget is per code, so an attacker holding a list of numbers
    gets five free guesses against each of them and trips nothing. This is the
    limit that notices the list.
    """

    scope = "otp_verify_caller"

    def get_cache_key(self, request, view) -> str | None:
        return self._key(self.get_ident(request))


def _requested_phone(request) -> str:
    """The number this request is about, or ``""`` if it does not say.

    Read off the parsed body rather than a serializer, because a throttle runs
    before the view and there is no validated data yet. A malformed body must
    never raise here: a throttle that can crash is a denial-of-service switch
    on the sign-in path.
    """
    try:
        value = request.data.get("phone", "")
    except Exception:  # pragma: no cover - unparseable body; DRF will 400 it
        return ""
    return value.strip() if isinstance(value, str) else ""


#: The set every path that can send a code must carry. Named, rather than
#: written out at each view, so that adding a third limit later reaches every
#: send path at once instead of reaching the ones somebody remembered — and so
#: `ops/checks/one_otp_rate_limit.py` has a single symbol to insist on.
OTP_SEND_THROTTLES: list[type[SimpleRateThrottle]] = [
    OtpSendPerPhoneThrottle,
    OtpSendPerCallerThrottle,
]

#: The same idea for the path that spends codes rather than sending them.
OTP_VERIFY_THROTTLES: list[type[SimpleRateThrottle]] = [OtpVerifyPerCallerThrottle]
