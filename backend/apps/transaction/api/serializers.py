from rest_framework import serializers
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer, TimestampFieldsMixin
from apps.transaction.models import Transaction, TransactionLog, TransactionFormMapping


class CreateInvitationInputSerializer(BaseInputSerializer):
    transaction_type = serializers.CharField(max_length=100)
    target_user_id = serializers.UUIDField()
    context_type = serializers.CharField(max_length=20)
    context_id = serializers.UUIDField()
    payload = serializers.JSONField(required=False, default=dict)
    form_response_id = serializers.UUIDField(required=False, allow_null=True)


class CreateRequestInputSerializer(BaseInputSerializer):
    transaction_type = serializers.CharField(max_length=100)
    target_account_id = serializers.UUIDField(required=False, allow_null=True)
    target_account_type = serializers.CharField(max_length=20, required=False, allow_null=True)
    target_user_id = serializers.UUIDField(required=False, allow_null=True)
    payload = serializers.JSONField(required=False, default=dict)
    form_response_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        if not data.get("target_account_id") and not data.get("target_user_id"):
            raise serializers.ValidationError(
                "Either target_account_id or target_user_id is required.",
            )
        return data


class AcceptTransactionInputSerializer(BaseInputSerializer):
    role_id = serializers.UUIDField(required=False, allow_null=True)
    form_response_id = serializers.UUIDField(required=False, allow_null=True)


class DenyTransactionInputSerializer(BaseInputSerializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=1000,
    )


class RequestInfoInputSerializer(BaseInputSerializer):
    message = serializers.CharField(max_length=2000)
    requested_fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True,
    )


class FormResponseUpdateInputSerializer(BaseInputSerializer):
    data = serializers.JSONField()


def _resolve_user(party_type, party_id, party_context=None):
    """Resolve a transaction party to a User object (or None)."""
    from apps.transaction.constants import PartyType
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if party_type == PartyType.USER:
        return User.objects.select_related("profile").filter(id=party_id).first()
    if party_type == PartyType.MEMBERSHIP_ACTOR:
        user_id = (party_context or {}).get("user_id")
        if user_id:
            return User.objects.select_related("profile").filter(id=user_id).first()
    return None


def _get_user_display_name(user):
    """Return display name for a user, or empty string."""
    if not user:
        return ""
    return user.get_short_name()


def _get_user_avatar_url(user):
    """Return avatar URL for a user, or None."""
    if not user or not hasattr(user, "profile"):
        return None
    profile = user.profile
    if profile.avatar:
        return profile.avatar.url
    return None


class TransactionLogOutputSerializer(BaseOutputSerializer):
    class Meta:
        model = TransactionLog
        fields = (
            "id", "event_type", "timestamp",
            "previous_status", "new_status", "metadata",
        )
        read_only_fields = fields


class TransactionOutputSerializer(BaseOutputSerializer, TimestampFieldsMixin):
    logs = TransactionLogOutputSerializer(many=True, read_only=True)
    form_response = serializers.SerializerMethodField()
    form_mapping = serializers.SerializerMethodField()
    initiator_name = serializers.SerializerMethodField()
    initiator_avatar_url = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    target_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id", "transaction_type", "mode", "initiator_type", "initiator_id",
            "initiator_context", "initiator_name", "initiator_avatar_url",
            "target_type", "target_id", "target_name", "target_avatar_url",
            "context_type", "context_id",
            "status", "payload", "form_response_id",
            "info_requested_at", "info_requested_message", "info_requested_fields",
            "expires_at", "resolved_at", "resolution_reason",
            "created_at", "updated_at", "logs", "form_response", "form_mapping",
        )
        read_only_fields = fields

    def get_form_response(self, obj):
        if not obj.form_response_id:
            return None
        from apps.forms.selectors import FormResponseSelector
        response = FormResponseSelector.get_by_id_or_none(
            response_id=obj.form_response_id,
        )
        if not response:
            return None
        return {
            "id": str(response.id),
            "form_template_id": str(response.form_template_id),
            "form_name": response.form_template.name if response.form_template else None,
            "status": response.status,
            "revision": response.revision,
            "submitted_at": response.submitted_at.isoformat() if response.submitted_at else None,
            "data": response.data,
        }

    def get_form_mapping(self, obj):
        from apps.transaction.selectors import TransactionSelector
        mapping = TransactionSelector.get_form_mapping_for_transaction(
            transaction=obj,
        )
        if not mapping:
            return None
        return {
            "id": str(mapping.id),
            "form_template_id": str(mapping.form_template_id),
            "form_template_name": mapping.form_template.name,
            "is_required": mapping.is_required,
        }

    def get_initiator_name(self, obj) -> str:
        user = _resolve_user(obj.initiator_type, obj.initiator_id, obj.initiator_context)
        return _get_user_display_name(user)

    def get_initiator_avatar_url(self, obj):
        user = _resolve_user(obj.initiator_type, obj.initiator_id, obj.initiator_context)
        return _get_user_avatar_url(user)

    def get_target_name(self, obj) -> str:
        from apps.transaction.constants import PartyType
        if obj.target_type == PartyType.ACCOUNT:
            from apps.organization.business.models import BusinessAccount
            biz = BusinessAccount.objects.filter(id=obj.target_id).first()
            if biz:
                return biz.legal_name
            return ""
        user = _resolve_user(obj.target_type, obj.target_id)
        return _get_user_display_name(user)

    def get_target_avatar_url(self, obj):
        from apps.transaction.constants import PartyType
        if obj.target_type == PartyType.ACCOUNT:
            return None
        user = _resolve_user(obj.target_type, obj.target_id)
        return _get_user_avatar_url(user)


class TransactionListSerializer(BaseOutputSerializer, TimestampFieldsMixin):
    category = serializers.SerializerMethodField()
    initiator_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id", "transaction_type", "mode", "status", "category",
            "initiator_type", "initiator_id", "initiator_name",
            "target_type", "target_id", "target_name",
            "context_type", "context_id",
            "expires_at", "created_at",
        )
        read_only_fields = fields

    def get_category(self, obj) -> str:
        from apps.transaction.types import TRANSACTION_TYPES
        config = TRANSACTION_TYPES.get(obj.transaction_type)
        return config.category if config else ""

    def get_initiator_name(self, obj) -> str:
        user = _resolve_user(obj.initiator_type, obj.initiator_id, obj.initiator_context)
        return _get_user_display_name(user)

    def get_target_name(self, obj) -> str:
        from apps.transaction.constants import PartyType
        if obj.target_type == PartyType.ACCOUNT:
            from apps.organization.business.models import BusinessAccount
            biz = BusinessAccount.objects.filter(id=obj.target_id).first()
            if biz:
                return biz.legal_name
            return ""
        user = _resolve_user(obj.target_type, obj.target_id)
        return _get_user_display_name(user)


# =========================================================================
# FORM MAPPING SERIALIZERS
# =========================================================================

class TransactionFormMappingOutputSerializer(BaseOutputSerializer, TimestampFieldsMixin):
    form_template_name = serializers.SerializerMethodField()

    class Meta:
        model = TransactionFormMapping
        fields = (
            "id", "account_type", "account_id", "transaction_type",
            "form_template_id", "form_template_name", "is_required",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_form_template_name(self, obj) -> str:
        if obj.form_template:
            return obj.form_template.name
        return ""


class TransactionFormMappingInputSerializer(BaseInputSerializer):
    transaction_type = serializers.CharField(max_length=100)
    form_template_id = serializers.UUIDField()
    is_required = serializers.BooleanField(default=False)
