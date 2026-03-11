# apps/core/visibility/serializers.py
"""
Serializer mixin and input serializer for the visibility system.

VisibilityAwareSerializerMixin: Add to any DRF output serializer to enable
field-level visibility filtering. Each serializer declares its own
`visibility_registry` class attribute.

VisibilityOverrideInput: Validates PATCH input for visibility settings.
"""

from rest_framework import serializers

from apps.core.visibility.registry import get_t2_fields, get_visibility_choices, get_account_type_for_registry
from apps.core.visibility.resolver import VisibilityResolver


class VisibilityAwareSerializerMixin:
    """Mixin that filters serialized output based on viewer access.

    Usage:
        class MyOutput(VisibilityAwareSerializerMixin, BaseOutputSerializer):
            visibility_registry = "business_profile"
            ...

    The view passes visibility context:
        serializer = MyOutput(instance, context={
            'request': request,
            'visibility': {
                'viewer_access': viewer_access,
                'visibility_overrides': profile.visibility_overrides,
                'is_public': profile.is_public,
            },
        })

    If no 'visibility' key in context, all fields pass through (backward compatible).
    """

    visibility_registry: str = ""  # Subclass MUST set

    def to_representation(self, instance):
        data = super().to_representation(instance)

        visibility_ctx = self.context.get("visibility")
        if visibility_ctx is None:
            return data  # Backward compatible — no filtering

        registry_key = self.visibility_registry
        if not registry_key:
            return data  # Safety: no registry declared → no filtering

        return VisibilityResolver.filter_fields(
            data=data,
            registry_key=registry_key,
            viewer_access=visibility_ctx["viewer_access"],
            visibility_overrides=visibility_ctx.get("visibility_overrides"),
            is_public=visibility_ctx.get("is_public", True),
        )


class VisibilityOverrideInput(serializers.Serializer):
    """Input serializer for PATCH /visibility/ endpoint.

    Validates that:
    - Only T2 field names are accepted
    - Level values are within the account type's enum range
    """

    overrides = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Map of field_name → visibility level",
    )

    def validate_overrides(self, value):
        registry_key = self.context.get("registry_key")
        if not registry_key:
            raise serializers.ValidationError(
                "Missing registry_key in serializer context."
            )

        t2_fields = get_t2_fields(registry_key)
        account_type = get_account_type_for_registry(registry_key)
        choices = get_visibility_choices(account_type)
        valid_values = {c.value for c in choices}

        errors = {}
        for field_name, level in value.items():
            if field_name not in t2_fields:
                errors[field_name] = f"'{field_name}' is not a configurable visibility field."
            elif level not in valid_values:
                errors[field_name] = (
                    f"Invalid level {level}. Valid values: {sorted(valid_values)}."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return value
