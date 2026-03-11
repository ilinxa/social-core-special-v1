# apps/organization/migrations/0006_add_visibility_overrides.py

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0005_businessaccount_open_member_request_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessprofile",
            name="visibility_overrides",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Per-field visibility level overrides for T2 fields.",
            ),
        ),
        migrations.AddField(
            model_name="platformprofile",
            name="visibility_overrides",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Per-field visibility level overrides for T2 fields.",
            ),
        ),
    ]
