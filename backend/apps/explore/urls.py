"""
Explore URL Configuration
=========================
"""

from django.urls import path

from apps.explore.views import (
    ExploreBusinessSearchView,
    ExploreCityListView,
    ExploreCombinedView,
    ExploreTagSuggestView,
    ExploreUserSearchView,
)

app_name = "explore"

urlpatterns = [
    path("", ExploreCombinedView.as_view(), name="combined"),
    path("businesses/", ExploreBusinessSearchView.as_view(), name="businesses"),
    path("users/", ExploreUserSearchView.as_view(), name="users"),
    path("tags/", ExploreTagSuggestView.as_view(), name="tags"),
    path("cities/", ExploreCityListView.as_view(), name="cities"),
]
