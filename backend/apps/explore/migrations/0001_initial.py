"""
Initial migration for explore app.

Creates:
- pg_trgm extension for trigram similarity search
- SuggestedTag model for tag autocomplete
"""

from django.db import migrations, models
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        TrigramExtension(),
        migrations.CreateModel(
            name="SuggestedTag",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=50, unique=True)),
                ("slug", models.SlugField(max_length=50, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("business", "Business"),
                            ("both", "Both"),
                        ],
                        default="both",
                        max_length=20,
                    ),
                ),
                ("usage_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "explore_suggested_tag",
                "verbose_name": "Suggested Tag",
                "verbose_name_plural": "Suggested Tags",
                "ordering": ["-usage_count", "name"],
            },
        ),
    ]
