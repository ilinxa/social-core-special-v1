# apps/users/migrations/0011_userprofile_visibility_overrides.py

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_add_cover_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="visibility_overrides",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Per-field visibility level overrides for T2 fields.",
            ),
        ),
    ]
