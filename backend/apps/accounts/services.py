"""Business rules about accounts.

Right now there is exactly one: what an account is called when a human looks at
it. It lives here because rules live in the service layer, and it lives *only*
here because a name computed in two places eventually disagrees with itself.
"""

from __future__ import annotations

from apps.accounts.models import Company, User


def display_name(user: User) -> str:
    """The one name any screen, report, export or message may show for ``user``.

    A company bids under the company's name, never under the name of whoever
    happens to represent it. In v1 some screens showed the representative and
    others the company, so support could not tell which account had placed a
    bid. Every caller asks this function; nobody assembles a name themselves.

    An account marked as a company but with no company row yet falls back to the
    person's own name — half-finished registration must not render blank.
    """
    try:
        company: Company = user.company
    except Company.DoesNotExist:
        return user.full_name
    return company.name
