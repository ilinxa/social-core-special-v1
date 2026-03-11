"""
Make system forms visible in the public template library.

System forms should appear in the library so any business/platform
can fork them for their own use.
"""
from django.db import migrations


SYSTEM_SLUGS = [
    "system-business-verification",
    "system-business-creation",
    "system-platform-staff-application",
]


def make_public(apps, schema_editor):
    FormTemplate = apps.get_model("forms", "FormTemplate")
    FormTemplate.objects.filter(
        owner_type="system",
        slug__in=SYSTEM_SLUGS,
    ).update(is_template_public=True)


def make_private(apps, schema_editor):
    FormTemplate = apps.get_model("forms", "FormTemplate")
    FormTemplate.objects.filter(
        owner_type="system",
        slug__in=SYSTEM_SLUGS,
    ).update(is_template_public=False)


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0003_seed_system_forms"),
    ]

    operations = [
        migrations.RunPython(make_public, make_private),
    ]
