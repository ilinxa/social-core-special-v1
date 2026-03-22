"""
Seed system forms for transaction integration.

Creates 3 system forms:
- system-business-verification (for business_verification_request)
- system-business-creation (for business_creation_permission_request)
- system-platform-staff-application (for future platform staff flow)
"""

from django.db import migrations
from django.utils import timezone

SYSTEM_FORMS = [
    {
        "slug": "system-business-verification",
        "name": "Business Verification Form",
        "description": "Required form for business verification requests",
        "scope": "business",
        "fields": [
            {
                "field_key": "legal_name",
                "field_type": "text",
                "label": "Legal Business Name",
                "order": 1,
                "is_required": True,
                "is_indexed": True,
                "step_tag": "business_info",
            },
            {
                "field_key": "registration_number",
                "field_type": "text",
                "label": "Registration Number",
                "order": 2,
                "is_required": True,
                "is_indexed": True,
                "step_tag": "business_info",
            },
            {
                "field_key": "tax_id",
                "field_type": "text",
                "label": "Tax Identification Number",
                "order": 3,
                "is_required": True,
                "is_indexed": True,
                "step_tag": "business_info",
            },
            {
                "field_key": "country",
                "field_type": "text",
                "label": "Country of Registration",
                "placeholder": "e.g. United States",
                "order": 4,
                "is_required": True,
                "is_indexed": True,
                "step_tag": "business_info",
            },
            {
                "field_key": "legal_address",
                "field_type": "textarea",
                "label": "Legal Address",
                "order": 5,
                "is_required": True,
                "step_tag": "address",
            },
            {
                "field_key": "business_license",
                "field_type": "file",
                "label": "Business License",
                "description": "Upload your business license document",
                "order": 6,
                "is_required": True,
                "step_tag": "documents",
            },
            {
                "field_key": "tax_certificate",
                "field_type": "file",
                "label": "Tax Certificate",
                "description": "Upload your tax certificate (optional)",
                "order": 7,
                "is_required": False,
                "step_tag": "documents",
            },
            {
                "field_key": "additional_documents",
                "field_type": "file",
                "label": "Additional Documents",
                "order": 8,
                "is_required": False,
                "step_tag": "documents",
            },
        ],
    },
    {
        "slug": "system-business-creation",
        "name": "Business Creation Form",
        "description": "Required form for business creation permission requests",
        "scope": "platform",
        "fields": [
            {
                "field_key": "legal_name",
                "field_type": "text",
                "label": "Legal Business Name",
                "order": 1,
                "is_required": True,
                "is_indexed": True,
            },
            {
                "field_key": "display_name",
                "field_type": "text",
                "label": "Display Name",
                "order": 2,
                "is_required": True,
            },
            {
                "field_key": "country",
                "field_type": "text",
                "label": "Country",
                "placeholder": "e.g. United States",
                "order": 3,
                "is_required": True,
                "is_indexed": True,
            },
            {
                "field_key": "business_type",
                "field_type": "select",
                "label": "Business Type",
                "order": 4,
                "is_required": True,
                "is_indexed": True,
                "options": [],
            },
            {
                "field_key": "description",
                "field_type": "textarea",
                "label": "Business Description",
                "order": 5,
                "is_required": False,
            },
            {
                "field_key": "website",
                "field_type": "url",
                "label": "Website",
                "order": 6,
                "is_required": False,
            },
        ],
    },
    {
        "slug": "system-platform-staff-application",
        "name": "Platform Staff Application",
        "description": "Application form for platform staff positions",
        "scope": "platform",
        "fields": [
            {
                "field_key": "motivation",
                "field_type": "textarea",
                "label": "Motivation",
                "description": "Why do you want to join the platform team?",
                "order": 1,
                "is_required": True,
            },
            {
                "field_key": "experience",
                "field_type": "textarea",
                "label": "Relevant Experience",
                "order": 2,
                "is_required": True,
            },
            {
                "field_key": "availability",
                "field_type": "select",
                "label": "Availability",
                "order": 3,
                "is_required": True,
                "is_indexed": True,
                "options": [
                    {"value": "full_time", "label": "Full Time"},
                    {"value": "part_time", "label": "Part Time"},
                    {"value": "weekends", "label": "Weekends Only"},
                ],
            },
            {
                "field_key": "linkedin_url",
                "field_type": "url",
                "label": "LinkedIn Profile",
                "order": 4,
                "is_required": False,
            },
            {
                "field_key": "resume",
                "field_type": "file",
                "label": "Resume / CV",
                "order": 5,
                "is_required": False,
            },
        ],
    },
]


def seed_system_forms(apps, schema_editor):
    FormTemplate = apps.get_model("forms", "FormTemplate")
    FormField = apps.get_model("forms", "FormField")

    now = timezone.now()
    system_context = {
        "user_id": None,
        "account_type": None,
        "account_id": None,
        "membership_id": None,
        "role_id": None,
        "role_name": None,
        "role_level": None,
        "is_owner": False,
        "permissions_snapshot": [],
        "captured_at": now.isoformat(),
        "ip_address": None,
        "user_agent": "system_migration",
    }

    for form_def in SYSTEM_FORMS:
        template = FormTemplate.objects.create(
            name=form_def["name"],
            slug=form_def["slug"],
            description=form_def["description"],
            owner_type="system",
            owner_id=None,
            scope=form_def["scope"],
            creator_context=system_context,
            status="active",
            version=1,
            is_current=True,
            settings={},
        )

        for field_def in form_def["fields"]:
            FormField.objects.create(
                form_template=template,
                field_key=field_def["field_key"],
                field_type=field_def["field_type"],
                label=field_def["label"],
                description=field_def.get("description", ""),
                placeholder=field_def.get("placeholder", ""),
                order=field_def["order"],
                step_tag=field_def.get("step_tag", ""),
                section_tag=field_def.get("section_tag", ""),
                options=field_def.get("options", []),
                validation_rules=field_def.get("validation_rules", {}),
                ui_config=field_def.get("ui_config", {}),
                default_value=field_def.get("default_value"),
                is_required=field_def.get("is_required", False),
                is_indexed=field_def.get("is_indexed", False),
                is_hidden=field_def.get("is_hidden", False),
                is_readonly=field_def.get("is_readonly", False),
            )


def remove_system_forms(apps, schema_editor):
    FormTemplate = apps.get_model("forms", "FormTemplate")
    slugs = [f["slug"] for f in SYSTEM_FORMS]
    FormTemplate.objects.filter(
        owner_type="system",
        slug__in=slugs,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0002_add_transaction_integration"),
    ]

    operations = [
        migrations.RunPython(seed_system_forms, remove_system_forms),
    ]
