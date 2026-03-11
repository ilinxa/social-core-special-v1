# Transaction System — Phase 3: Interface Layer

**Implements:** API views, serializers, URLs, TransactionContextMixin, Celery tasks, rate limiting.  
**Depends on:** Phase 2 complete.  
**Deliverable:** REST endpoints callable. Background tasks scheduled. Integration tests pass.

---

## 1. Serializers

```python
# apps/transaction/api/serializers.py
from rest_framework import serializers
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer, TimestampFieldsMixin
from apps.transaction.models import Transaction, TransactionLog


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
        """Ensure either target_account_id or target_user_id is provided."""
        if not data.get("target_account_id") and not data.get("target_user_id"):
            raise serializers.ValidationError("Either target_account_id or target_user_id is required.")
        return data


class DenyTransactionInputSerializer(BaseInputSerializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class TransactionLogOutputSerializer(BaseOutputSerializer):
    class Meta:
        model = TransactionLog
        fields = ("id", "event_type", "timestamp", "previous_status", "new_status", "metadata")
        read_only_fields = fields


class TransactionOutputSerializer(BaseOutputSerializer, TimestampFieldsMixin):
    logs = TransactionLogOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id", "transaction_type", "mode", "initiator_type", "initiator_id",
            "initiator_context",
            "target_type", "target_id", "context_type", "context_id",
            "status", "payload", "expires_at", "resolved_at", "resolution_reason",
            "created_at", "updated_at", "logs",
        )
        read_only_fields = fields


class TransactionListSerializer(BaseOutputSerializer, TimestampFieldsMixin):
    class Meta:
        model = Transaction
        fields = ("id", "transaction_type", "mode", "status", "expires_at", "created_at")
        read_only_fields = fields
```

---

## 2. Views

**Critical:** `TransactionContextMixin` resolves the correct ActorContext type per approver policy. `TARGET_ACCEPTANCE` gets user-level context. `ACCOUNT_AUTHORITY`/`PLATFORM_AUTHORITY` get account-bound context via `RBACService.build_actor_context()`.

```python
# apps/transaction/api/views.py
from uuid import UUID
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import IsAuthenticated
from apps.core.pagination import StandardPagination
from apps.core.types import ActorContext
from apps.rbac.services import RBACService
from apps.rbac.selectors import MembershipSelector

from apps.transaction.api.serializers import (
    CreateInvitationInputSerializer, CreateRequestInputSerializer,
    DenyTransactionInputSerializer, TransactionOutputSerializer, TransactionListSerializer,
)
from apps.transaction.selectors import TransactionSelector
from apps.transaction.services import TransactionService
from apps.transaction.policies import TransactionPolicy
from apps.transaction.types import get_transaction_type
from apps.transaction.constants import ApproverPolicy


class TransactionContextMixin:
    """Resolve correct ActorContext for transaction approval/denial actions."""

    def get_actor_context_for_transaction(self, request, transaction):
        config = get_transaction_type(transaction.transaction_type)

        if config.approver_policy == ApproverPolicy.TARGET_ACCEPTANCE:
            return ActorContext.for_user_context(request.user, request)

        if config.approver_policy in (ApproverPolicy.ACCOUNT_AUTHORITY, ApproverPolicy.PLATFORM_AUTHORITY):
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=transaction.context_type,
                account_id=transaction.context_id,
            )
            if not membership:
                from apps.core.exceptions import PermissionDenied
                raise PermissionDenied(
                    message="Not a member of the account this transaction belongs to",
                    action="resolve_transaction", resource="Transaction",
                )
            return RBACService.build_actor_context(membership=membership, request=request)

        return ActorContext.for_user_context(request.user, request)


class TransactionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = TransactionListSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        role = self.request.query_params.get("role", "all")
        if role == "initiator":
            return TransactionSelector.list_for_user_as_initiator(user_id=user_id, include_terminal=True)
        elif role == "target":
            return TransactionSelector.list_for_user_as_target(user_id=user_id, include_terminal=True)
        else:
            i = TransactionSelector.list_for_user_as_initiator(user_id=user_id, include_terminal=True)
            t = TransactionSelector.list_for_user_as_target(user_id=user_id, include_terminal=True)
            return i.union(t).order_by("-created_at")


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id_with_logs(transaction_id=transaction_id)
        actor_context = ActorContext.for_user_context(request.user, request)
        TransactionPolicy.can_view(transaction=txn, actor_context=actor_context)
        return Response(TransactionOutputSerializer(txn, context={"request": request}).data)


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CreateInvitationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user, account_type=data["context_type"], account_id=data["context_id"],
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied
            raise PermissionDenied(message="Not a member of this account",
                                   action="create_invitation", resource="Transaction")

        actor_context = RBACService.build_actor_context(membership=membership, request=request)

        txn = TransactionService.create_invitation(
            transaction_type=data["transaction_type"],
            initiator_context=actor_context,
            target_user_id=data["target_user_id"],
            payload=data.get("payload", {}),
            form_response_id=data.get("form_response_id"),
            request=request,
        )
        return Response(
            TransactionOutputSerializer(txn, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CreateRequestView(APIView):
    permission_classes = [IsAuthenticated]

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
            TransactionOutputSerializer(txn, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AcceptTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.accept(transaction_id=transaction_id, actor_context=actor_context, request=request)
        return Response(TransactionOutputSerializer(result, context={"request": request}).data)


class DenyTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, transaction_id: UUID):
        ser = DenyTransactionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.deny(
            transaction_id=transaction_id, actor_context=actor_context,
            reason=ser.validated_data.get("reason", ""), request=request,
        )
        return Response(TransactionOutputSerializer(result, context={"request": request}).data)


class CancelTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, transaction_id: UUID):
        actor_context = ActorContext.for_user_context(request.user, request)
        result = TransactionService.cancel(transaction_id=transaction_id, actor_context=actor_context, request=request)
        return Response(TransactionOutputSerializer(result, context={"request": request}).data)


class DismissTransactionView(TransactionContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, transaction_id: UUID):
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        actor_context = self.get_actor_context_for_transaction(request, txn)
        result = TransactionService.dismiss(transaction_id=transaction_id, actor_context=actor_context, request=request)
        return Response(TransactionOutputSerializer(result, context={"request": request}).data)
```

---

## 3. URLs

```python
# apps/transaction/api/urls.py
from django.urls import path
from apps.transaction.api.views import (
    TransactionListView, TransactionDetailView,
    CreateInvitationView, CreateRequestView,
    AcceptTransactionView, DenyTransactionView,
    CancelTransactionView, DismissTransactionView,
)

app_name = "transaction"

urlpatterns = [
    path("", TransactionListView.as_view(), name="list"),
    path("invitation/", CreateInvitationView.as_view(), name="create-invitation"),
    path("request/", CreateRequestView.as_view(), name="create-request"),
    path("<uuid:transaction_id>/", TransactionDetailView.as_view(), name="detail"),
    path("<uuid:transaction_id>/accept/", AcceptTransactionView.as_view(), name="accept"),
    path("<uuid:transaction_id>/deny/", DenyTransactionView.as_view(), name="deny"),
    path("<uuid:transaction_id>/cancel/", CancelTransactionView.as_view(), name="cancel"),
    path("<uuid:transaction_id>/dismiss/", DismissTransactionView.as_view(), name="dismiss"),
]
```

Add to `backend_core/urls.py`:

```python
urlpatterns = [
    # ... existing ...
    path("api/v1/transactions/", include("apps.transaction.api.urls")),
]
```

---

## 4. Background Tasks

```python
# apps/transaction/tasks.py
from celery import shared_task
from django.utils import timezone
from apps.core.observability.logging.celery import LoggedTask
from apps.core.observability import get_logger
from apps.transaction.selectors import TransactionSelector

logger = get_logger(__name__)


@shared_task(base=LoggedTask)
def expire_transactions_task():
    """Hourly: expire transactions past their expiration date."""
    expired = TransactionSelector.list_expired_needing_update()
    count = 0
    for txn in expired:
        from apps.transaction.services import TransactionService
        try:
            TransactionService.expire(transaction_id=txn.id)
            count += 1
        except Exception as e:
            logger.error("task.expire.failed", transaction_id=str(txn.id), error=str(e))
    logger.info("task.expire.complete", count=count)


@shared_task(bind=True, base=LoggedTask, max_retries=3)
def retry_outcome_execution_task(self, transaction_id: str):
    """Retry failed outcome execution with exponential backoff."""
    from uuid import UUID
    from apps.transaction.services import TransactionService
    from apps.core.types import ActorContext

    try:
        txn = TransactionSelector.get_by_id(transaction_id=UUID(transaction_id))
        if txn.outcome_executed:
            return
        TransactionService._execute_outcome(transaction=txn, actor_context=ActorContext.for_system())
    except Exception as exc:
        logger.error("task.retry_outcome.failed", transaction_id=transaction_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@shared_task(base=LoggedTask)
def cleanup_old_transaction_logs_task(retention_days: int = 90):
    """Daily: delete logs for terminal transactions older than retention."""
    from apps.transaction.models import TransactionLog
    from apps.transaction.constants import TERMINAL_STATES

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    deleted, _ = TransactionLog.objects.filter(
        timestamp__lt=cutoff, transaction__status__in=list(TERMINAL_STATES),
    ).delete()
    logger.info("task.cleanup.complete", deleted=deleted)


@shared_task(base=LoggedTask)
def send_expiration_reminder_task():
    """Daily: remind targets about transactions expiring in 24-48 hours."""
    from apps.transaction.models import Transaction
    from django.contrib.auth import get_user_model
    User = get_user_model()

    now = timezone.now()
    expiring = Transaction.objects.filter(
        expires_at__gte=now + timezone.timedelta(hours=24),
        expires_at__lt=now + timezone.timedelta(hours=48),
        status="pending",
    )

    try:
        from apps.notifications.services import NotificationService
    except ImportError:
        return

    count = 0
    for txn in expiring:
        if txn.mode == "invitation" and txn.target_type == "user":
            target = User.objects.filter(id=txn.target_id).first()
            if target:
                NotificationService.send(
                    user=target, notification_type="transaction_expiring_soon",
                    context={"transaction_id": str(txn.id), "expires_at": txn.expires_at.isoformat()},
                )
                count += 1
    logger.info("task.reminder.complete", count=count)
```

### Celery Beat Configuration

Add to `backend_core/celery.py`:

```python
CELERY_BEAT_SCHEDULE = {
    # ... existing ...
    "expire-transactions": {
        "task": "apps.transaction.tasks.expire_transactions_task",
        "schedule": crontab(minute=0),  # Every hour
    },
    "transaction-expiration-reminders": {
        "task": "apps.transaction.tasks.send_expiration_reminder_task",
        "schedule": crontab(hour=9, minute=0),  # Daily 9 AM
    },
    "cleanup-transaction-logs": {
        "task": "apps.transaction.tasks.cleanup_old_transaction_logs_task",
        "schedule": crontab(hour=3, minute=0),  # Daily 3 AM
    },
}
```

---

## 5. Rate Limiting

```python
# apps/transaction/rate_limits.py
from django.core.cache import cache
from apps.core.exceptions import RateLimitExceeded

RATE_LIMITS = {
    "user_requests_per_hour": 10,
    "user_connection_requests_per_day": 20,
    "business_invitations_per_day": 50,
    "resubmissions_per_day_per_target": 3,
}

RATE_TTLS = {
    "per_hour": 3600,
    "per_day": 86400,
}


def check_rate_limit(user_id, limit_type, ttl_type="per_hour"):
    cache_key = f"txn_rate:{limit_type}:{user_id}"
    current = cache.get(cache_key, 0)
    limit = RATE_LIMITS.get(limit_type, 100)

    if current >= limit:
        raise RateLimitExceeded(
            message=f"Rate limit exceeded for {limit_type}",
            retry_after=RATE_TTLS.get(ttl_type, 3600),
        )

    cache.set(cache_key, current + 1, timeout=RATE_TTLS.get(ttl_type, 3600))
```

Add rate limit checks at the top of `TransactionService.create_invitation()` and `create_request()`:

```python
from apps.transaction.rate_limits import check_rate_limit
# In create_invitation:
check_rate_limit(str(initiator_context.user_id), "business_invitations_per_day", "per_day")
# In create_request:
check_rate_limit(str(user_id), "user_requests_per_hour", "per_hour")
```

---

## 6. Phase 3 Verification

```bash
# Run API tests
pytest apps/transaction/tests/test_views.py -v

# Check URL routing
python manage.py show_urls | grep transaction

# Check Celery tasks registered
python manage.py shell -c "
from apps.transaction.tasks import expire_transactions_task, retry_outcome_execution_task
print('Tasks OK')
"

# Full test suite
pytest apps/transaction/ -v
```
