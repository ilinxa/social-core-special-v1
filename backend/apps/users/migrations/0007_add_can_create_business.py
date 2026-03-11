# Generated manually for business creation gating

from django.db import migrations, models


def grant_existing_business_owners(apps, schema_editor):
    """
    Set can_create_business=True for users who already own a business.

    This ensures backwards compatibility — existing business owners
    retain their ability to create businesses after the policy change.
    """
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET can_create_business = TRUE
                WHERE id IN (
                    SELECT DISTINCT user_id FROM rbac_membership
                    WHERE is_owner = TRUE AND account_type = 'business'
                    AND is_deleted = FALSE
                )
            """)
    else:
        # SQLite path for unit tests
        Membership = apps.get_model("rbac", "Membership")
        User = apps.get_model("users", "User")
        owner_user_ids = (
            Membership.objects.filter(
                is_owner=True,
                account_type="business",
                is_deleted=False,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )
        User.objects.filter(id__in=owner_user_ids).update(can_create_business=True)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_alter_user_id"),
        ("rbac", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="can_create_business",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text="Designates whether user has been approved to create business accounts.",
            ),
        ),
        migrations.RunPython(
            grant_existing_business_owners,
            migrations.RunPython.noop,
        ),
    ]
