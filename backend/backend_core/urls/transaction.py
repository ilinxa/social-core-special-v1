"""
Transaction URL routes — invitations, requests, approvals.

Gated by systems.transaction in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path(
        "api/v1/transactions/",
        include("apps.transaction.api.urls", namespace="transaction"),
    ),
]
