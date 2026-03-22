from django.contrib import admin

from apps.forms.models import FormField, FormResponse, FormTemplate


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0
    ordering = ["order"]
    fields = ["field_key", "field_type", "label", "order", "is_required", "is_indexed"]
    readonly_fields = ["field_key"]


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "owner_type",
        "scope",
        "status",
        "version",
        "is_current",
        "created_at",
    ]
    list_filter = ["status", "owner_type", "scope", "is_current", "is_template_public"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "creator_context", "created_at", "updated_at"]
    inlines = [FormFieldInline]


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "form_template",
        "submitted_by",
        "status",
        "submitted_at",
        "processed_at",
    ]
    list_filter = ["status"]
    search_fields = ["id"]
    readonly_fields = ["id", "submitter_context", "created_at", "updated_at"]
    raw_id_fields = ["form_template", "submitted_by", "processed_by"]


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = [
        "field_key",
        "form_template",
        "field_type",
        "label",
        "order",
        "is_required",
        "is_indexed",
    ]
    list_filter = ["field_type", "is_required", "is_indexed"]
    search_fields = ["field_key", "label", "form_template__name"]
    raw_id_fields = ["form_template"]
    readonly_fields = ["id"]
    ordering = ["form_template", "order"]
