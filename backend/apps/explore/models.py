"""
Explore Models
==============
Models supporting the search and discovery system.

Models:
    - SuggestedTag: Curated tag suggestions for autocomplete in the explore UI.
"""

from django.db import models
from django.utils.text import slugify


class TagCategory(models.TextChoices):
    USER = "user", "User"
    BUSINESS = "business", "Business"
    BOTH = "both", "Both"


class SuggestedTag(models.Model):
    """
    Curated tag suggestions for the explore autocomplete.

    Users and businesses can use any free-form tag, but the UI suggests from
    this table first. The usage_count field allows sorting by popularity.
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True)
    category = models.CharField(
        max_length=20,
        choices=TagCategory.choices,
        default=TagCategory.BOTH,
    )
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "explore_suggested_tag"
        ordering = ["-usage_count", "name"]
        verbose_name = "Suggested Tag"
        verbose_name_plural = "Suggested Tags"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
