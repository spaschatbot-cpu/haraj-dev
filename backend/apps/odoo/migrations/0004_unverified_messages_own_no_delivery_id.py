"""T913 — a delivery id belongs to a delivery the sender vouched for.

The unique index gains a `rejected_signature` exclusion. Before it, an
unsigned message stored at either webhook (Article 2-2 says store it)
reserved its own delivery id, so a stranger could post `{"id": 4711}` and
make the genuine, signed delivery 4711 be answered with "already stored"
and never interpreted.

Nothing in the data changes. Rows already stored keep their ids; the index
simply stops counting the unverified ones, which can only ever make a
previously-refused insert succeed.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("money", "0005_invoice_invoice_paid_not_above_amount"),
        ("odoo", "0003_alter_inboundmessage_payload_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="inboundmessage",
            name="one_row_per_delivery",
        ),
        migrations.AddConstraint(
            model_name="inboundmessage",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    models.Q(("delivery_id", ""), _negated=True),
                    models.Q(("state", "rejected_signature"), _negated=True),
                ),
                fields=("source", "delivery_id"),
                name="one_row_per_delivery",
            ),
        ),
    ]
