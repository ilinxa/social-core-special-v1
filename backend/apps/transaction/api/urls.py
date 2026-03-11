from django.urls import path
from apps.transaction.api.views import (
    TransactionListView,
    TransactionDetailView,
    CreateInvitationView,
    CreateRequestView,
    AcceptTransactionView,
    ApproveTransactionReviewView,
    DenyTransactionView,
    CancelTransactionView,
    DismissTransactionView,
    TransactionFormSchemaView,
    TransactionTypeListView,
    TransactionRequestInfoView,
    TransactionResubmitView,
    TransactionFormResponseView,
    TransactionRequiredFormView,
    RequestFormCheckView,
    TransactionFormMappingListCreateView,
    TransactionFormMappingDeleteView,
)

app_name = "transaction"

urlpatterns = [
    path("", TransactionListView.as_view(), name="list"),
    path("invitation/", CreateInvitationView.as_view(), name="create-invitation"),
    path("request/", CreateRequestView.as_view(), name="create-request"),
    path("types/", TransactionTypeListView.as_view(), name="type-list"),
    path("types/<str:transaction_type>/form/", TransactionFormSchemaView.as_view(), name="form-schema"),
    path("form-mappings/check/", RequestFormCheckView.as_view(), name="request-form-check"),
    path("form-mappings/", TransactionFormMappingListCreateView.as_view(), name="form-mapping-list-create"),
    path("form-mappings/<uuid:mapping_id>/", TransactionFormMappingDeleteView.as_view(), name="form-mapping-delete"),
    path("<uuid:transaction_id>/", TransactionDetailView.as_view(), name="detail"),
    path("<uuid:transaction_id>/accept/", AcceptTransactionView.as_view(), name="accept"),
    path("<uuid:transaction_id>/approve/", ApproveTransactionReviewView.as_view(), name="approve"),
    path("<uuid:transaction_id>/deny/", DenyTransactionView.as_view(), name="deny"),
    path("<uuid:transaction_id>/cancel/", CancelTransactionView.as_view(), name="cancel"),
    path("<uuid:transaction_id>/dismiss/", DismissTransactionView.as_view(), name="dismiss"),
    path("<uuid:transaction_id>/request-info/", TransactionRequestInfoView.as_view(), name="request-info"),
    path("<uuid:transaction_id>/resubmit/", TransactionResubmitView.as_view(), name="resubmit"),
    path("<uuid:transaction_id>/form-response/", TransactionFormResponseView.as_view(), name="form-response"),
    path("<uuid:transaction_id>/required-form/", TransactionRequiredFormView.as_view(), name="required-form"),
]
