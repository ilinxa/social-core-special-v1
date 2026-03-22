from uuid import UUID

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAuthenticated
from apps.core.types import ActorContext
from apps.core.views import PermissionInjectMixin
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService
from apps.transaction.api.serializers import (
    AcceptTransactionInputSerializer,
    CreateInvitationInputSerializer,
    CreateRequestInputSerializer,
    DenyTransactionInputSerializer,
    FormResponseUpdateInputSerializer,
    RequestInfoInputSerializer,
    TransactionFormMappingInputSerializer,
    TransactionFormMappingOutputSerializer,
    TransactionListSerializer,
    TransactionOutputSerializer,
)
from apps.transaction.constants import ApproverPolicy, PartyType, TransactionStatus
from apps.transaction.models import Transaction, TransactionFormMapping
from apps.transaction.policies import TransactionPolicy
from apps.transaction.selectors import TransactionSelector
from apps.transaction.services import TransactionService
from apps.transaction.types import get_transaction_type

User = get_user_model()


class TransactionContextMixin:
    """Resolve correct ActorContext for transaction approval/denial actions."""

    def get_actor_context_for_transaction(self, request, transaction):
        config = get_transaction_type(transaction.transaction_type)

        # For PENDING_REVIEW transactions, the account authority approves/denies
        # regardless of the original approver_policy (which may be TARGET_ACCEPTANCE
        # for invitations). Try to build an account context first; fall back to
        # user context if the viewer isn't a member (policy will deny).
        if transaction.status == TransactionStatus.PENDING_REVIEW:
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=transaction.context_type,
                account_id=transaction.context_id,
            )
            if membership:
                return RBACService.build_actor_context(
                    membership=membership,
                    request=request,
                )
            return ActorContext.for_user_context(request.user, request)

        if config.approver_policy == ApproverPolicy.TARGET_ACCEPTANCE:
            return ActorContext.for_user_context(request.user, request)

        if config.approver_policy in (
            ApproverPolicy.ACCOUNT_AUTHORITY,
            ApproverPolicy.PLATFORM_AUTHORITY,
        ):
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=transaction.context_type,
                account_id=transaction.context_id,
            )
            if not membership:
                from apps.core.exceptions import PermissionDenied

                raise PermissionDenied(
                    message="Not a member of the account this transaction belongs to",
                    action="resolve_transaction",
                    resource="Transaction",
                )
            return RBACService.build_actor_context(
                membership=membership,
                request=request,
            )

        return ActorContext.for_user_context(request.user, request)


class TransactionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = TransactionListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = page if page is not None else list(queryset)
        extra_context = self._batch_load_parties(items)
        serializer = self.get_serializer(items, many=True)
        serializer.context.update(extra_context)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def _batch_load_parties(self, transactions):
        """Batch-load User and BusinessAccount objects for party resolution."""
        from apps.organization.business.models import BusinessAccount

        user_ids = set()
        account_ids = set()
        for txn in transactions:
            if txn.initiator_type == PartyType.USER:
                user_ids.add(txn.initiator_id)
            elif txn.initiator_type == PartyType.MEMBERSHIP_ACTOR:
                uid = (txn.initiator_context or {}).get("user_id")
                if uid:
                    user_ids.add(UUID(uid) if isinstance(uid, str) else uid)
            if txn.target_type == PartyType.USER:
                user_ids.add(txn.target_id)
            elif txn.target_type == PartyType.ACCOUNT:
                account_ids.add(txn.target_id)

        party_users = {}
        if user_ids:
            for u in User.objects.select_related("profile").filter(id__in=user_ids):
                party_users[u.id] = u

        party_accounts = {}
        if account_ids:
            for a in BusinessAccount.objects.filter(id__in=account_ids):
                party_accounts[a.id] = a

        return {"party_users": party_users, "party_accounts": party_accounts}

    def get_queryset(self):
        user_id = self.request.user.id
        params = self.request.query_params
        role = params.get("role", "all")

        context_type = params.get("context_type")
        context_id = params.get("context_id")

        # When both context_type and context_id are provided, use account-level
        # querying: return all transactions within that account context.
        # This is used by bconsole/pconsole to see incoming requests, sent
        # invitations, etc. — regardless of who personally initiated/received them.
        # Access is gated by membership (verified below).
        if context_type and context_id:
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=self.request.user,
                account_type=context_type,
                account_id=context_id,
            )

            if membership:
                # Member: full account-level view
                qs = TransactionSelector.list_for_context(
                    context_type=context_type,
                    context_id=context_id,
                    include_terminal=True,
                )
                # Filter out permission-gated transaction types the viewer can't approve
                actor_context = RBACService.build_actor_context(
                    membership=membership,
                    request=self.request,
                )
                qs = TransactionSelector.apply_permission_filters(qs, actor_context)
            elif role in ("initiator", "target"):
                # Non-member with explicit role: show only their own
                # transactions within this context (e.g., pending membership
                # request they sent to a business they haven't joined yet).
                if role == "initiator":
                    qs = TransactionSelector.list_for_user_as_initiator(
                        user_id=user_id,
                        include_terminal=True,
                    )
                else:
                    qs = TransactionSelector.list_for_user_as_target(
                        user_id=user_id,
                        include_terminal=True,
                    )
                qs = qs.filter(context_type=context_type, context_id=context_id)
            else:
                return Transaction.objects.none()

            mode = params.get("mode")
            status_filter = params.get("status")
            transaction_type = params.get("transaction_type")

            if mode:
                qs = qs.filter(mode=mode)
            if status_filter:
                qs = qs.filter(status=status_filter)
            if transaction_type:
                qs = qs.filter(transaction_type=transaction_type)

            return qs

        # User-level querying (no account context specified)
        if role == "initiator":
            qs = TransactionSelector.list_for_user_as_initiator(
                user_id=user_id,
                include_terminal=True,
            )
        elif role == "target":
            qs = TransactionSelector.list_for_user_as_target(
                user_id=user_id,
                include_terminal=True,
            )
        else:
            i = TransactionSelector.list_for_user_as_initiator(
                user_id=user_id,
                include_terminal=True,
            )
            t = TransactionSelector.list_for_user_as_target(
                user_id=user_id,
                include_terminal=True,
            )
            qs = i.order_by().union(t.order_by()).order_by("-created_at")

        # Apply filters (only when not using UNION — UNION doesn't support filter)
        mode = params.get("mode")
        status_filter = params.get("status")
        transaction_type = params.get("transaction_type")

        has_filters = any([mode, status_filter, transaction_type])
        if has_filters and role == "all":
            # Re-query without UNION to support filtering
            qs = TransactionSelector.list_for_user(
                user_id=user_id,
                include_terminal=True,
            )

        if mode:
            qs = qs.filter(mode=mode)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)

        return qs


class TransactionDetailView(TransactionContextMixin, PermissionInjectMixin, APIView):
    permission_classes = [IsAuthenticated]
    policy_class = TransactionPolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "transaction": self._transaction,
            "actor_context": self._rich_actor_context,
        }

    @extend_schema(
        summary="Get transaction",
        description="Get details of a transaction including its state log.",
        tags=["Transaction"],
        responses={200: TransactionOutputSerializer},
    )
    def get(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id_with_logs(
            transaction_id=transaction_id,
        )
        # Build richest possible context first — account members need
        # account-level context for can_view() to check account_id/is_owner.
        user_context = ActorContext.for_user_context(request.user, request)
        try:
            rich_ctx = self.get_actor_context_for_transaction(request, txn)
        except Exception:
            rich_ctx = user_context
        TransactionPolicy.can_view(
            transaction=txn,
            actor_context=rich_ctx,
        )
        self._transaction = txn
        self._rich_actor_context = rich_ctx
        self._inject_permissions = True
        return Response(
            TransactionOutputSerializer(
                txn,
                context={"request": request},
            ).data,
        )


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create invitation",
        description="Create a new invitation transaction.",
        tags=["Transaction"],
        request=CreateInvitationInputSerializer,
        responses={201: TransactionOutputSerializer},
    )
    def post(self, request):
        ser = CreateInvitationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=data["context_type"],
            account_id=data["context_id"],
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Not a member of this account",
                action="create_invitation",
                resource="Transaction",
            )

        actor_context = RBACService.build_actor_context(
            membership=membership,
            request=request,
        )

        txn = TransactionService.create_invitation(
            transaction_type=data["transaction_type"],
            initiator_context=actor_context,
            target_user_id=data["target_user_id"],
            payload=data.get("payload", {}),
            form_response_id=data.get("form_response_id"),
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                txn,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class CreateRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create request",
        description="Create a new request transaction.",
        tags=["Transaction"],
        request=CreateRequestInputSerializer,
        responses={201: TransactionOutputSerializer},
    )
    def post(self, request):
        ser = CreateRequestInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        txn = TransactionService.create_request(
            transaction_type=data["transaction_type"],
            user_id=request.user.id,
            target_account_type=data.get("target_account_type"),
            target_account_id=data.get("target_account_id"),
            target_user_id=data.get("target_user_id"),
            payload=data.get("payload", {}),
            form_response_id=data.get("form_response_id"),
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                txn,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AcceptTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Accept transaction",
        description="Accept a pending transaction. Optionally provide role_id for membership approvals.",
        tags=["Transaction"],
        request=AcceptTransactionInputSerializer,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        acceptance_payload = {}
        if request.data:
            ser = AcceptTransactionInputSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            acceptance_payload = {
                k: v for k, v in ser.validated_data.items() if v is not None
            }

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.accept(
            transaction_id=transaction_id,
            actor_context=actor_context,
            acceptance_payload=acceptance_payload,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class ApproveTransactionReviewView(TransactionContextMixin, APIView):
    """Approve a PENDING_REVIEW transaction (business approves the submitted form)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Approve pending review",
        description="Approve a transaction that is pending form review. Activates the membership.",
        tags=["Transaction"],
        request=None,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.approve_pending_review(
            transaction_id=transaction_id,
            actor_context=actor_context,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class DenyTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Deny transaction",
        description="Deny a pending transaction with an optional reason.",
        tags=["Transaction"],
        request=DenyTransactionInputSerializer,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        ser = DenyTransactionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.deny(
            transaction_id=transaction_id,
            actor_context=actor_context,
            reason=ser.validated_data.get("reason", ""),
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class CancelTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel transaction",
        description="Cancel a pending transaction (initiator only).",
        tags=["Transaction"],
        request=None,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        actor_context = ActorContext.for_user_context(request.user, request)
        result = TransactionService.cancel(
            transaction_id=transaction_id,
            actor_context=actor_context,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class DismissTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dismiss transaction",
        description="Dismiss a completed or denied transaction.",
        tags=["Transaction"],
        request=None,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.dismiss(
            transaction_id=transaction_id,
            actor_context=actor_context,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class TransactionFormSchemaView(APIView):
    """GET form schema for a transaction type."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get transaction form schema",
        description="Get the form template schema for a transaction type.",
        tags=["Transaction"],
    )
    def get(self, request, transaction_type: str):
        from apps.forms.api.serializers import FormTemplateDetailOutputSerializer

        form_template = TransactionSelector.get_form_template_for_type(
            transaction_type=transaction_type,
        )
        if not form_template:
            return Response({"form_template": None})
        return Response(
            {
                "form_template": FormTemplateDetailOutputSerializer(
                    form_template,
                    context={"request": request},
                ).data,
            }
        )


class TransactionTypeListView(APIView):
    """GET list of all transaction types with their configuration."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List transaction types",
        description="List all available transaction types with their configuration.",
        tags=["Transaction"],
    )
    def get(self, request):
        from apps.transaction.types import TRANSACTION_TYPES

        context_type = request.query_params.get("context_type")

        types_list = []
        for _type_id, config in TRANSACTION_TYPES.items():
            if context_type and config.context_type != context_type:
                continue
            if not config.enabled:
                continue
            types_list.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "mode": config.mode,
                    "category": config.category,
                    "context_type": config.context_type,
                    "initiator_types": config.initiator_types,
                    "target_types": config.target_types,
                    "approver_policy": config.approver_policy,
                    "required_permissions": config.required_permissions,
                    "owner_only": config.owner_only,
                    "requires_form": config.requires_form,
                    "has_optional_form": config.has_optional_form,
                    "expiration_days": config.expiration_days,
                    "user_configurable": config.user_configurable,
                }
            )
        return Response(types_list)


class TransactionRequestInfoView(TransactionContextMixin, APIView):
    """POST to request more info from initiator."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Request more info",
        description="Request additional information from the transaction initiator.",
        tags=["Transaction"],
        request=RequestInfoInputSerializer,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        ser = RequestInfoInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)

        result = TransactionService.request_info(
            transaction_id=transaction_id,
            message=data["message"],
            requested_fields=data.get("requested_fields"),
            actor_context=actor_context,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class TransactionResubmitView(APIView):
    """POST to resubmit after updating form response."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Resubmit transaction",
        description="Resubmit a transaction after updating form response data.",
        tags=["Transaction"],
        request=None,
        responses={200: TransactionOutputSerializer},
    )
    def post(self, request, transaction_id: UUID):
        actor_context = ActorContext.for_user_context(request.user, request)
        result = TransactionService.resubmit_after_info_request(
            transaction_id=transaction_id,
            actor_context=actor_context,
            request=request,
        )
        return Response(
            TransactionOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class TransactionFormResponseView(APIView):
    """GET/PATCH form response linked to a transaction."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get transaction form response",
        description="Get the form response linked to a transaction.",
        tags=["Transaction"],
    )
    def get(self, request, transaction_id: UUID):
        from apps.forms.api.serializers import FormResponseDetailOutputSerializer
        from apps.forms.selectors import FormResponseSelector

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = ActorContext.for_user_context(request.user, request)
        TransactionPolicy.can_view(
            transaction=txn,
            actor_context=actor_context,
        )

        if not txn.form_response_id:
            return Response({"form_response": None})

        response = FormResponseSelector.get_by_id(
            response_id=txn.form_response_id,
        )
        return Response(
            FormResponseDetailOutputSerializer(
                response,
                context={"request": request},
            ).data,
        )

    @extend_schema(
        summary="Update transaction form response",
        description="Update the form response linked to a transaction.",
        tags=["Transaction"],
        request=FormResponseUpdateInputSerializer,
    )
    def patch(self, request, transaction_id: UUID):
        from apps.forms.services import FormResponseService

        ser = FormResponseUpdateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        if not txn.form_response_id:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="Transaction has no form response",
                field="form_response_id",
            )

        actor_context = ActorContext.for_user_context(request.user, request)
        result = FormResponseService.update_after_info_request(
            response_id=txn.form_response_id,
            data=ser.validated_data["data"],
            actor_context=actor_context,
            actor=request.user,
            request=request,
        )

        from apps.forms.api.serializers import FormResponseDetailOutputSerializer

        return Response(
            FormResponseDetailOutputSerializer(
                result,
                context={"request": request},
            ).data,
        )


class TransactionRequiredFormView(TransactionContextMixin, APIView):
    """GET form template required by a transaction's form mapping.
    POST to create and submit a form response for the transaction.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get required form template for transaction",
        description="Get the form template that must be filled before accepting this transaction.",
        tags=["Transaction"],
    )
    def get(self, request, transaction_id: UUID):
        from apps.forms.api.serializers import FormTemplateDetailOutputSerializer
        from apps.forms.selectors import FormResponseSelector

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        # Build richest possible context — account members need account-level
        # context for can_view() to check account_id/is_owner.
        user_context = ActorContext.for_user_context(request.user, request)
        try:
            actor_context = self.get_actor_context_for_transaction(request, txn)
        except Exception:
            actor_context = user_context
        TransactionPolicy.can_view(
            transaction=txn,
            actor_context=actor_context,
        )

        # If a response already exists, return the template it was submitted
        # against (may differ from mapping if mapping was changed since).
        if txn.form_response_id:
            form_response = FormResponseSelector.get_by_id_or_none(
                response_id=txn.form_response_id,
            )
            if form_response and form_response.form_template:
                mapping = TransactionSelector.get_form_mapping_for_transaction(
                    transaction=txn,
                )
                return Response(
                    {
                        "form_template": FormTemplateDetailOutputSerializer(
                            form_response.form_template,
                            context={"request": request},
                        ).data,
                        "is_required": mapping.is_required if mapping else False,
                    }
                )

        mapping = TransactionSelector.get_form_mapping_for_transaction(
            transaction=txn,
        )
        if not mapping:
            return Response({"form_template": None})

        return Response(
            {
                "form_template": FormTemplateDetailOutputSerializer(
                    mapping.form_template,
                    context={"request": request},
                ).data,
                "is_required": mapping.is_required,
            }
        )

    @extend_schema(
        summary="Submit required form for transaction",
        description="Create and submit a form response for the transaction's required form. "
        "Bypasses account membership checks — any transaction party can submit.",
        tags=["Transaction"],
        request=FormResponseUpdateInputSerializer,
    )
    def post(self, request, transaction_id: UUID):
        from apps.forms.api.serializers import FormResponseDetailOutputSerializer
        from apps.forms.services import FormResponseService

        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = ActorContext.for_user_context(request.user, request)
        TransactionPolicy.can_view(
            transaction=txn,
            actor_context=actor_context,
        )

        mapping = TransactionSelector.get_form_mapping_for_transaction(
            transaction=txn,
        )
        if not mapping:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="No form mapping exists for this transaction",
                field="form_mapping",
            )

        ser = FormResponseUpdateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        response = FormResponseService.create_and_submit(
            form_template=mapping.form_template,
            data=ser.validated_data["data"],
            context_type=txn.context_type,
            context_id=txn.context_id,
            actor_context=actor_context,
            actor=request.user,
            request=request,
        )

        return Response(
            FormResponseDetailOutputSerializer(
                response,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


# =========================================================================
# FORM MAPPING CHECK (pre-creation form lookup + submit)
# =========================================================================


class RequestFormCheckView(APIView):
    """Check if a form is required before creating a request, and submit responses.

    GET  ?transaction_type=X&account_type=Y&account_id=Z
         Returns form mapping + form template fields if mapping exists.
    POST {form_mapping_id, data: {...}}
         Creates and submits a form response for the form template in the mapping.
    """

    permission_classes = []  # GET is public, POST checks auth inline

    @extend_schema(
        summary="Check request form requirement",
        description="Check if a form mapping exists for creating a request to this account.",
        tags=["Transaction"],
    )
    def get(self, request):
        transaction_type = request.query_params.get("transaction_type")
        account_type = request.query_params.get("account_type")
        account_id = request.query_params.get("account_id")

        if not all([transaction_type, account_type, account_id]):
            return Response({"form_required": False})

        mapping = (
            TransactionFormMapping.objects.filter(
                account_type=account_type,
                account_id=account_id,
                transaction_type=transaction_type,
                is_deleted=False,
            )
            .select_related("form_template")
            .first()
        )

        if not mapping:
            return Response({"form_required": False})

        from apps.forms.api.serializers import FormTemplateDetailOutputSerializer

        return Response(
            {
                "form_required": mapping.is_required,
                "form_mapping_id": str(mapping.id),
                "form_template": FormTemplateDetailOutputSerializer(
                    mapping.form_template,
                    context={"request": request},
                ).data,
            }
        )

    @extend_schema(
        summary="Submit form for request",
        description="Create and submit a form response before creating a request. "
        "Returns the form_response_id to include in the create-request call.",
        tags=["Transaction"],
    )
    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Authentication required",
                action="submit_request_form",
                resource="FormResponse",
            )

        mapping_id = request.data.get("form_mapping_id")
        form_data = request.data.get("data", {})

        if not mapping_id:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="form_mapping_id is required",
                field="form_mapping_id",
            )

        mapping = (
            TransactionFormMapping.objects.filter(
                id=mapping_id,
                is_deleted=False,
            )
            .select_related("form_template")
            .first()
        )
        if not mapping:
            from apps.core.exceptions import NotFound

            raise NotFound(
                resource="TransactionFormMapping",
                resource_id=str(mapping_id),
            )

        from apps.forms.services import FormResponseService

        actor_context = ActorContext.for_user_context(request.user, request)
        response = FormResponseService.create_and_submit(
            form_template=mapping.form_template,
            data=form_data,
            context_type=mapping.account_type,
            context_id=mapping.account_id,
            actor_context=actor_context,
            actor=request.user,
            request=request,
        )

        return Response(
            {"form_response_id": str(response.id)},
            status=status.HTTP_201_CREATED,
        )


# =========================================================================
# FORM MAPPING VIEWS
# =========================================================================


class TransactionFormMappingListCreateView(APIView):
    """List and create form mappings for a context."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List form mappings",
        description="List transaction form mappings for the given account context.",
        tags=["Transaction"],
        responses={200: TransactionFormMappingOutputSerializer(many=True)},
    )
    def get(self, request):
        account_type = request.query_params.get("account_type")
        account_id = request.query_params.get("account_id")
        if not account_type or not account_id:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="account_type and account_id are required",
                field="account_type",
            )

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=account_type,
            account_id=account_id,
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Not a member of this account",
                action="list_form_mappings",
                resource="TransactionFormMapping",
            )
        actor_context = RBACService.build_actor_context(
            membership=membership,
            request=request,
        )
        if not actor_context.has_permission("can_configure_transactions"):
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Missing can_configure_transactions permission",
                action="list_form_mappings",
                resource="TransactionFormMapping",
            )

        mappings = (
            TransactionFormMapping.objects.filter(
                account_type=account_type,
                account_id=account_id,
                is_deleted=False,
            )
            .select_related("form_template")
            .order_by("transaction_type")
        )
        return Response(
            TransactionFormMappingOutputSerializer(mappings, many=True).data,
        )

    @extend_schema(
        summary="Create form mapping",
        description="Create a transaction form mapping for the given account context.",
        tags=["Transaction"],
        request=TransactionFormMappingInputSerializer,
        responses={201: TransactionFormMappingOutputSerializer},
    )
    def post(self, request):
        # Build actor context - require membership with can_configure_transactions
        account_type = request.data.get("account_type") or request.query_params.get(
            "account_type"
        )
        account_id = request.data.get("account_id") or request.query_params.get(
            "account_id"
        )
        if not account_type or not account_id:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="account_type and account_id are required",
                field="account_type",
            )

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=account_type,
            account_id=account_id,
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Not a member of this account",
                action="create_form_mapping",
                resource="TransactionFormMapping",
            )
        actor_context = RBACService.build_actor_context(
            membership=membership,
            request=request,
        )
        if not actor_context.has_permission("can_configure_transactions"):
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Missing can_configure_transactions permission",
                action="create_form_mapping",
                resource="TransactionFormMapping",
            )

        ser = TransactionFormMappingInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        mapping = TransactionFormMapping.objects.create(
            account_type=account_type,
            account_id=account_id,
            transaction_type=data["transaction_type"],
            form_template_id=data["form_template_id"],
            is_required=data.get("is_required", False),
            created_by=request.user,
        )
        return Response(
            TransactionFormMappingOutputSerializer(mapping).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionFormMappingDeleteView(APIView):
    """Delete a form mapping."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete form mapping",
        description="Delete a transaction form mapping.",
        tags=["Transaction"],
        responses={204: None},
    )
    def delete(self, request, mapping_id: UUID):
        mapping = TransactionFormMapping.objects.filter(
            id=mapping_id,
            is_deleted=False,
        ).first()
        if not mapping:
            from apps.core.exceptions import NotFound

            raise NotFound(
                resource="TransactionFormMapping",
                resource_id=str(mapping_id),
            )

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=mapping.account_type,
            account_id=mapping.account_id,
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Not a member of this account",
                action="delete_form_mapping",
                resource="TransactionFormMapping",
            )
        actor_context = RBACService.build_actor_context(
            membership=membership,
            request=request,
        )
        if not actor_context.has_permission("can_configure_transactions"):
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Missing can_configure_transactions permission",
                action="delete_form_mapping",
                resource="TransactionFormMapping",
            )

        mapping.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
