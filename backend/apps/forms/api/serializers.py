from rest_framework import serializers
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.core.constants import FieldType, OwnerType, FormScope
from apps.forms.models import FormTemplate, FormField, FormResponse


# ============================================================================
# INPUT SERIALIZERS
# ============================================================================

class FormTemplateCreateInputSerializer(BaseInputSerializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    owner_type = serializers.ChoiceField(choices=OwnerType.choices)
    owner_id = serializers.UUIDField(required=False, allow_null=True)
    scope = serializers.ChoiceField(choices=FormScope.choices)
    settings = serializers.JSONField(required=False, default=dict)


class FormTemplateUpdateInputSerializer(BaseInputSerializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    settings = serializers.JSONField(required=False)


class FormFieldCreateInputSerializer(BaseInputSerializer):
    field_key = serializers.CharField(max_length=100)
    field_type = serializers.ChoiceField(choices=FieldType.choices)
    label = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    placeholder = serializers.CharField(required=False, allow_blank=True, default="")
    order = serializers.IntegerField(min_value=0)
    step_tag = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    section_tag = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    options = serializers.ListField(required=False, default=list)
    validation_rules = serializers.JSONField(required=False, default=dict)
    ui_config = serializers.JSONField(required=False, default=dict)
    default_value = serializers.JSONField(required=False, allow_null=True)
    is_required = serializers.BooleanField(default=False)
    is_indexed = serializers.BooleanField(default=False)
    is_hidden = serializers.BooleanField(default=False)
    is_readonly = serializers.BooleanField(default=False)


class FormResponseCreateInputSerializer(BaseInputSerializer):
    data = serializers.JSONField()


class FormResponseUpdateInputSerializer(BaseInputSerializer):
    data = serializers.JSONField()


class FormResponseProcessInputSerializer(BaseInputSerializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FormResponseVoidInputSerializer(BaseInputSerializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateFieldInputSerializer(BaseInputSerializer):
    label = serializers.CharField(max_length=200, required=False)
    help_text = serializers.CharField(max_length=500, required=False, allow_blank=True)
    placeholder = serializers.CharField(max_length=200, required=False, allow_blank=True)
    options = serializers.JSONField(required=False)
    validation_rules = serializers.JSONField(required=False)
    is_required = serializers.BooleanField(required=False)
    is_indexable = serializers.BooleanField(required=False)
    section_tag = serializers.CharField(max_length=100, required=False, allow_blank=True)
    step_tag = serializers.CharField(max_length=100, required=False, allow_blank=True)
    conditional_logic = serializers.JSONField(required=False)


class ReorderFieldInputSerializer(BaseInputSerializer):
    field_id = serializers.UUIDField()
    order = serializers.IntegerField(min_value=0)


class ReorderFieldsInputSerializer(BaseInputSerializer):
    fields = ReorderFieldInputSerializer(many=True)


class ForkTemplateInputSerializer(BaseInputSerializer):
    new_owner_type = serializers.ChoiceField(choices=OwnerType.choices)
    new_owner_id = serializers.UUIDField()
    new_name = serializers.CharField(max_length=255, required=False)
    new_slug = serializers.SlugField(max_length=100, required=False)


# ============================================================================
# OUTPUT SERIALIZERS
# ============================================================================

class FormFieldOutputSerializer(BaseOutputSerializer):
    class Meta:
        model = FormField
        fields = [
            "id", "field_key", "field_type", "label", "description",
            "placeholder", "order", "step_tag", "section_tag", "options",
            "validation_rules", "ui_config", "default_value",
            "is_required", "is_indexed", "is_hidden", "is_readonly",
        ]
        read_only_fields = fields


class FormTemplateListOutputSerializer(BaseOutputSerializer):
    class Meta:
        model = FormTemplate
        fields = [
            "id", "name", "slug", "description", "owner_type",
            "scope", "status", "version", "is_current",
            "is_template_public", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FormTemplateDetailOutputSerializer(BaseOutputSerializer):
    fields = FormFieldOutputSerializer(many=True, read_only=True)
    forked_from_name = serializers.CharField(
        source="forked_from.name",
        read_only=True,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = FormTemplate
        fields = [
            "id", "name", "slug", "description", "owner_type", "owner_id",
            "scope", "status", "version", "is_current", "parent_version",
            "is_template_public", "forked_from", "forked_from_name",
            "settings", "fields", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FormResponseListOutputSerializer(BaseOutputSerializer):
    form_name = serializers.CharField(source="form_template.name", read_only=True)
    submitter_email = serializers.CharField(source="submitted_by.email", read_only=True)
    submitter_username = serializers.CharField(source="submitted_by.username", read_only=True)
    submitter_display_name = serializers.SerializerMethodField()

    class Meta:
        model = FormResponse
        fields = [
            "id", "form_template", "form_name", "form_version",
            "submitted_by", "submitter_email", "submitter_username",
            "submitter_display_name", "data", "status",
            "submitted_at", "processed_at", "created_at",
        ]
        read_only_fields = fields

    def get_submitter_display_name(self, obj) -> str:
        user = obj.submitted_by
        if hasattr(user, "profile") and user.profile and user.profile.display_name:
            return user.profile.display_name
        return user.email.split("@")[0]


class FormResponseDetailOutputSerializer(BaseOutputSerializer):
    form_name = serializers.CharField(source="form_template.name", read_only=True)
    submitter_email = serializers.CharField(source="submitted_by.email", read_only=True)
    submitter_username = serializers.CharField(source="submitted_by.username", read_only=True)
    submitter_display_name = serializers.SerializerMethodField()
    processor_email = serializers.CharField(
        source="processed_by.email",
        read_only=True,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = FormResponse
        fields = [
            "id", "form_template", "form_name", "form_version",
            "submitted_by", "submitter_email", "submitter_username",
            "submitter_display_name", "submitter_context",
            "data", "status", "submitted_at", "processed_at",
            "processed_by", "processor_email", "processor_notes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_submitter_display_name(self, obj) -> str:
        user = obj.submitted_by
        if hasattr(user, "profile") and user.profile and user.profile.display_name:
            return user.profile.display_name
        return user.email.split("@")[0]
