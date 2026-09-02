"""Two branches numbered their migration 0002 at the same time.

Phase 002 added the hold constraints; phase 007 added PaymentIntent and
RefundRequest. Neither touches what the other touches, so this joins the two
leaves rather than renumbering either — renumbering would rewrite a migration
that has already been applied somewhere, which is the one thing a migration
must never do.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("money", "0002_hold_one_active_hold_per_customer_and_invoice_and_more"),
        ("money", "0002_paymentintent_refundrequest"),
    ]

    operations = []
