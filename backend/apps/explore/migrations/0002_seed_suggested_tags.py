"""
Data migration to seed initial SuggestedTag entries.

These provide autocomplete suggestions for the explore search UI.
Categories: 'user', 'business', 'both'.
"""

from django.db import migrations
from django.utils.text import slugify


TAGS = [
    # Both (user + business)
    ("technology", "both"),
    ("ai", "both"),
    ("machine-learning", "both"),
    ("blockchain", "both"),
    ("sustainability", "both"),
    ("marketing", "both"),
    ("design", "both"),
    ("finance", "both"),
    ("healthcare", "both"),
    ("education", "both"),
    ("real-estate", "both"),
    ("media", "both"),
    ("entertainment", "both"),
    ("sports", "both"),
    ("travel", "both"),
    ("food-beverage", "both"),
    ("fashion", "both"),
    ("automotive", "both"),
    ("energy", "both"),
    ("agriculture", "both"),
    # Business-oriented
    ("saas", "business"),
    ("e-commerce", "business"),
    ("fintech", "business"),
    ("b2b", "business"),
    ("b2c", "business"),
    ("startup", "business"),
    ("enterprise", "business"),
    ("consulting", "business"),
    ("logistics", "business"),
    ("manufacturing", "business"),
    ("retail", "business"),
    ("hospitality", "business"),
    ("construction", "business"),
    ("telecommunications", "business"),
    ("insurance", "business"),
    # User-oriented
    ("developer", "user"),
    ("designer", "user"),
    ("entrepreneur", "user"),
    ("freelancer", "user"),
    ("investor", "user"),
    ("mentor", "user"),
    ("content-creator", "user"),
    ("data-scientist", "user"),
    ("product-manager", "user"),
    ("engineer", "user"),
    ("photographer", "user"),
    ("writer", "user"),
    ("consultant", "user"),
    ("researcher", "user"),
    ("student", "user"),
]


def seed_tags(apps, schema_editor):
    SuggestedTag = apps.get_model("explore", "SuggestedTag")
    for name, category in TAGS:
        SuggestedTag.objects.get_or_create(
            name=name,
            defaults={
                "slug": slugify(name),
                "category": category,
                "usage_count": 0,
                "is_active": True,
            },
        )


def reverse_tags(apps, schema_editor):
    SuggestedTag = apps.get_model("explore", "SuggestedTag")
    tag_names = [name for name, _ in TAGS]
    SuggestedTag.objects.filter(name__in=tag_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("explore", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tags, reverse_tags),
    ]
