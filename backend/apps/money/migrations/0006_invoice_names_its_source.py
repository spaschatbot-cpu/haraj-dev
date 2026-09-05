"""HR-05 — every invoice records where it was born.

The backfill says ``local`` because that is what every row written before this
migration is: the only path that had created invoices was ``issue_invoice``,
and the Odoo mirror is what this field exists to tell apart from it. Written by
hand rather than answered at a `makemigrations` prompt so the choice is in the
repository with its reason, and not in one developer's terminal history.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("money", "0005_invoice_invoice_paid_not_above_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="source",
            field=models.CharField(
                choices=[("local", "محلية"), ("odoo_sync", "من أودو")],
                default="local",
                max_length=16,
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.CheckConstraint(
                condition=models.Q(source__in=["local", "odoo_sync"]),
                name="invoice_names_its_source",
            ),
        ),
    ]
