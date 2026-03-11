# apps/network/urls.py
from django.urls import path

from apps.network import views

app_name = "network"

urlpatterns = [
    # Follow
    path("follow/", views.FollowCreateView.as_view(), name="follow-create"),
    path("follow/<uuid:follow_id>/", views.FollowDeleteView.as_view(), name="follow-delete"),
    path("following/", views.FollowingListView.as_view(), name="following-list"),

    # User connections
    path("connections/request/", views.UserConnectionRequestView.as_view(), name="connection-request"),
    path("connections/<uuid:connection_id>/", views.UserConnectionDeleteView.as_view(), name="connection-delete"),
    path("connections/", views.UserConnectionListView.as_view(), name="connection-list"),

    # Business followers
    path("business/<slug:slug>/followers/", views.BusinessFollowersListView.as_view(), name="business-followers"),
    path("business/<slug:slug>/followers/<uuid:follow_id>/", views.BusinessFollowerRemoveView.as_view(), name="business-follower-remove"),

    # Business connections
    path("business/<slug:slug>/connections/request/", views.BusinessConnectionRequestView.as_view(), name="business-connection-request"),
    path("business/<slug:slug>/connections/<uuid:connection_id>/", views.BusinessConnectionDeleteView.as_view(), name="business-connection-delete"),
    path("business/<slug:slug>/connections/", views.BusinessConnectionListView.as_view(), name="business-connection-list"),

    # Stats
    path("stats/", views.UserNetworkStatsView.as_view(), name="user-stats"),
    path("business/<slug:slug>/stats/", views.BusinessNetworkStatsView.as_view(), name="business-stats"),
]
