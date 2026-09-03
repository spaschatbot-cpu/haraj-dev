"""T912 — the stored path stops being the uploader's to choose.

A schema-only change: `upload_to` moves from a path template, which keeps
the submitted file name on the end, to a callable that mints the whole name.
Rows already written keep the names they have — nothing here rewrites a
stored path, and nothing needs to: the old names are what the old files are
called on disk. New uploads get generated ones.
"""


import apps.core.uploads
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0003_favourite"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicleimage",
            name="image",
            field=models.ImageField(upload_to=apps.core.uploads.vehicle_image_path),
        ),
        migrations.AlterField(
            model_name="vehicleimage",
            name="thumbnail",
            field=models.ImageField(
                blank=True, upload_to=apps.core.uploads.vehicle_thumbnail_path
            ),
        ),
    ]
