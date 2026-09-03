"""المفضّلة — «تابِعني هذه المركبة» كصفٍّ في القاعدة لا كحالة في متصفّح.

A customer marks a car and expects to find it marked on their phone, on the
website, and tomorrow. That sentence is the whole design brief and it decides
the only question this file has: where does the mark live?

Not in the client
-----------------
The tempting answer is `localStorage`, or a list in the app's own database. It
is wrong for a reason that has nothing to do with technology: **a favourite the
customer sees on the site and not in the app is a bug in the product**, not a
missing sync. Two channels serving one contract is the phase's governing
principle, and a feature stored per-channel is that principle abandoned for
whichever feature seemed small enough.

So it is a row, keyed by (customer, vehicle), and both channels read the same
endpoint.

What a favourite is *not*
-------------------------
It is not a claim on anything. It moves no money, reserves no car, and gives no
priority — a bidder with a hundred favourites has exactly the standing of one
with none. That is worth writing down because "watchlist" features grow
expectations: the moment a favourite implies notification or precedence, it
becomes a promise the platform has to keep, and this one deliberately promises
only that the customer can find the car again.

Idempotent on purpose
---------------------
Marking twice is marking once, and unmarking something unmarked is not an error.
Both are what a double-tapped button and a retried request produce, and a
"favourite already exists" refusal would be a sentence a customer cannot act on
for a thing that already happened the way they wanted.
"""

from __future__ import annotations

from django.conf import settings
from django.db import IntegrityError, models, transaction

__all__ = ["Favourite", "favourite_ids", "mark", "unmark"]


class Favourite(models.Model):
    """One customer's mark on one vehicle."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favourites"
    )
    vehicle = models.ForeignKey(
        "auctions.Vehicle", on_delete=models.CASCADE, related_name="favourited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # One mark per pair. The uniqueness is what makes marking twice a
            # no-op rather than two rows — enforced here rather than by a
            # read-then-write in the service, because a check against a row that
            # a second request is inserting at the same moment is not a check.
            models.UniqueConstraint(
                fields=["user", "vehicle"], name="one_favourite_per_customer_and_vehicle"
            ),
        ]
        indexes = [
            # "What has this customer marked?", newest first — the only question
            # the list screen asks.
            models.Index(fields=["user", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} ♥ {self.vehicle_id}"


def mark(*, user, vehicle) -> Favourite:
    """Mark a vehicle. Marking again returns the existing mark.

    `CASCADE` on both sides, deliberately and unusually for this codebase, where
    almost everything is `PROTECT`: a favourite is the one row here that carries
    no history worth keeping. A deleted account or a purged vehicle should take
    its marks with it, and a `PROTECT` would make deleting either impossible for
    the sake of a bookmark.
    """
    try:
        # A savepoint of its own. `ATOMIC_REQUESTS` wraps the whole request, and
        # an `IntegrityError` raised inside it poisons that transaction — every
        # later query, including the `get` below, would fail with
        # `TransactionManagementError`. The inner atomic block is what keeps the
        # failed insert a *recoverable* one.
        with transaction.atomic():
            return Favourite.objects.create(user=user, vehicle=vehicle)
    except IntegrityError:
        # Two taps arriving together: the second lost the race to the unique
        # index, and the row it wanted is already there. That is success.
        return Favourite.objects.get(user=user, vehicle=vehicle)


def unmark(*, user, vehicle=None, vehicle_id=None) -> bool:
    """Remove a mark. Returns whether there was one to remove.

    Takes a vehicle *or* just its id, because the delete path deliberately does
    not load the row: a customer tidying their list may be unmarking a car that
    has since been withdrawn from sight, and making them fetch it first would
    leave a mark they can see and cannot remove.

    Never raises for an absent mark either. Unmarking something already unmarked
    is what a retried request produces, and the customer's intent is satisfied
    either way.
    """
    if vehicle is not None:
        vehicle_id = vehicle.pk
    deleted, _ = Favourite.objects.filter(user=user, vehicle_id=vehicle_id).delete()
    return bool(deleted)


def favourite_ids(user, vehicles) -> set[int]:
    """Which of ``vehicles`` this customer has marked — one query, not one each.

    Used to answer `is_favourite` on a list of cards. Computed for the whole
    page at once because the alternative is a query per row, which is how a
    listing goes from one query to twenty-one without anybody noticing until the
    page is slow in production (T614's lesson, in a different app).

    An anonymous caller has no favourites, and asking is not an error: the
    browse pages are public and the same serializer renders for both.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return set()

    return set(
        Favourite.objects.filter(user=user, vehicle__in=vehicles).values_list(
            "vehicle_id", flat=True
        )
    )
