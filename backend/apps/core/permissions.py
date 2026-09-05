"""Who may do what. One gate, one question, one place. T801.

The question this module answers is **"may this person do Y?"** — never "is
this person an X?". The difference is not style, and v1 paid for it: `hasRole()`
there returned true for every role when the asker was the owner, which read as
generous until somebody used it to ask *"is this user's role X?"* about a
specific person. For the owner it answered yes to every role at once, the menu
code took the first match, and the console locked the owner out of his own
platform.

So the rule (spec 009 §"قواعد الصلاحيات"):

1. one gate, :func:`can`, used by every screen and every endpoint;
2. **no function anywhere asks about a role** — `ops/checks/one_permission_gate.py`
   fails the build when one appears;
3. the owner holds everything, and that is expressed as *a role that lists every
   capability*, not as a branch that short-circuits the check. A special case in
   the gate is a special case that eventually answers the wrong question.

Capabilities are enumerated here and nowhere else. A screen guarded by a string
nobody declared is a screen guarded by a typo.
"""

from __future__ import annotations

from django.db import models


class Capability(models.TextChoices):
    """Everything the console can be asked to permit.

    Named for the *thing being done*, not for the screen doing it: two screens
    that read the same rows share a capability, and a screen that both reads and
    writes carries two. `auctions.view` and `auctions.manage` are separate
    because "look at the calendar" and "change what is in it" are different
    trusts — v1 had one flag for both, so anybody who could check a date could
    also cancel a lot.
    """

    # The console itself. Without this nothing else is reachable, so it is the
    # one capability every staff role carries.
    CONSOLE_ACCESS = "console.access", "دخول اللوحة"

    AUCTIONS_VIEW = "auctions.view", "عرض المزادات والمركبات"
    AUCTIONS_MANAGE = "auctions.manage", "إدارة المزادات والمركبات"
    AUCTIONS_IMPORT = "auctions.import", "استيراد وتصدير المركبات"

    PARTNERS_DECIDE = "partners.decide", "قرارات الشريك واختيار العروض"

    USERS_VIEW = "users.view", "عرض المستخدمين والشركات"
    USERS_MANAGE = "users.manage", "إدارة المستخدمين والشركات"

    INVOICES_VIEW = "invoices.view", "عرض الفواتير والمدفوعات"

    # `invoices.manage` كانت هنا، وكانت ممنوحةً للمالك والمالية، **ولا تحرس
    # صفحةً واحدة**: لا صفَّ لها في `navigation.PAGES` ولا `require()` يطلبها.
    # فأُزيلت، لأن قدرةً كهذه ليست شيفرةً ميّتة — هي **جملةٌ كاذبة في نموذج
    # الصلاحيات**. من يسأل «من يستطيع إدارة الفواتير؟» يقرأ الاسم تحت
    # FINANCE فيستنتج طريقاً محكوماً، ولا باب أصلاً.
    #
    # وإصدار فاتورةٍ أو تسجيل دفعةٍ بيد موظّف ما زال **غير مبنيّ** — وهو تاسك
    # في `apps/money` (المسار أ)، لا حذفٌ هنا. يوم يُبنى، تعود القدرة مع
    # صفحتها في `PAGES`، ويمرّ حارس `every_capability_guards_something`.

    # Money is split three ways on purpose. Reading the ledger, acting on it,
    # and granting an exception are three different levels of trust, and v1
    # collapsed them into "finance" — so anybody who could read a balance could
    # also confiscate a deposit.
    MONEY_VIEW = "money.view", "عرض دفتر التأمينات والحركات"
    MONEY_ACT = "money.act", "الأفعال المالية الإدارية"
    MONEY_EXCEPTION = "money.exception", "منح استثناء تأمين"

    DIAGNOSTICS_VIEW = "diagnostics.view", "شاشات التشخيص وصحة المال"
    ODOO_INBOX = "odoo.inbox", "صندوق وارد أودو"
    AUDIT_VIEW = "audit.view", "سجل التدقيق"


class Role(models.TextChoices):
    """A named bundle of capabilities. A convenience, never an authority.

    Nothing in the codebase asks what somebody's role is; a role exists only to
    say which capabilities a person starts with. That is what makes the owner's
    "everything" safe to express — see :data:`ROLE_CAPABILITIES`.
    """

    OWNER = "owner", "المالك"
    OPERATIONS = "operations", "التشغيل"
    FINANCE = "finance", "المالية"
    SUPPORT = "support", "الدعم"


#: Which capabilities each role starts with.
#:
#: The owner's entry lists **every capability explicitly** rather than being a
#: `return True` in the gate. That is the whole lesson of the v1 incident: a
#: short-circuit is invisible at the call site and answers questions nobody
#: meant to ask. Written out, it is also a list somebody can read and audit —
#: and a new capability that the owner should not have is a deliberate omission
#: rather than an accident of wildcard.
ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    Role.OWNER: frozenset(Capability.values),
    Role.OPERATIONS: frozenset(
        {
            Capability.CONSOLE_ACCESS,
            Capability.AUCTIONS_VIEW,
            Capability.AUCTIONS_MANAGE,
            Capability.AUCTIONS_IMPORT,
            Capability.PARTNERS_DECIDE,
            Capability.USERS_VIEW,
            Capability.INVOICES_VIEW,
            Capability.DIAGNOSTICS_VIEW,
        }
    ),
    Role.FINANCE: frozenset(
        {
            Capability.CONSOLE_ACCESS,
            Capability.AUCTIONS_VIEW,
            Capability.USERS_VIEW,
            Capability.INVOICES_VIEW,
            Capability.MONEY_VIEW,
            Capability.MONEY_ACT,
            Capability.DIAGNOSTICS_VIEW,
            Capability.ODOO_INBOX,
            Capability.AUDIT_VIEW,
        }
    ),
    # Support answers questions; it does not move money or change auctions.
    # `diagnostics.view` is the point of the role — "why can't he bid?" is
    # support's most-asked question and it needs no write anywhere.
    Role.SUPPORT: frozenset(
        {
            Capability.CONSOLE_ACCESS,
            Capability.AUCTIONS_VIEW,
            Capability.USERS_VIEW,
            Capability.INVOICES_VIEW,
            Capability.MONEY_VIEW,
            Capability.DIAGNOSTICS_VIEW,
        }
    ),
}


def capabilities_of(user) -> frozenset[str]:
    """Everything ``user`` may do: their role's bundle, plus and minus grants.

    Order matters and is the answer to "why can she still not open that page
    after I gave her the grant?": a revoke beats a grant, and a grant beats the
    role. Support needs to be able to take something away from one person
    without editing a role that a dozen others share.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return frozenset()
    if not getattr(user, "is_staff", False):
        # The console is staff-only. A customer's token reaching a console view
        # is a routing bug, and answering "no capabilities" makes it look like
        # one instead of like a permission problem.
        return frozenset()

    from apps.accounts.models import StaffGrant

    allowed = set(ROLE_CAPABILITIES.get(getattr(user, "console_role", ""), frozenset()))

    grants = StaffGrant.objects.filter(user=user)
    for grant in grants:
        if grant.granted:
            allowed.add(grant.capability)
        else:
            allowed.discard(grant.capability)

    return frozenset(allowed)


def can(user, capability: str) -> bool:
    """May ``user`` do ``capability``? The only permission question in the code.

    Every screen, every endpoint, every menu item asks this and nothing else.
    There is no `is_owner`, no `has_role`, and no `if user.console_role == ...`
    anywhere — `ops/checks/one_permission_gate.py` fails the build on all three.
    """
    return capability in capabilities_of(user)


def require(user, capability: str) -> None:
    """Raise unless ``user`` may do ``capability``.

    A separate function from :func:`can` because a view that forgets to *act* on
    a `can()` result is the classic way a guard becomes decoration. This one
    cannot be ignored.
    """
    from django.core.exceptions import PermissionDenied

    if not can(user, capability):
        raise PermissionDenied(f"{capability} غير مسموحة لهذا المستخدم")


__all__ = [
    "ROLE_CAPABILITIES",
    "Capability",
    "Role",
    "can",
    "capabilities_of",
    "require",
]
