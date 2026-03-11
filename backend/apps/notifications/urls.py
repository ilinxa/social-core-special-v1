"""
Notification URLs
=================
URL configuration for notification app.
"""

from django.urls import path

from apps.notifications import views

app_name = 'notifications'

urlpatterns = [
    # Preferences
    path(
        'preferences/',
        views.PreferencesView.as_view(),
        name='preferences'
    ),
    path(
        'preferences/<str:notification_type>/',
        views.PreferenceDetailView.as_view(),
        name='preference-detail'
    ),

    # History
    path(
        'history/',
        views.NotificationHistoryView.as_view(),
        name='history'
    ),

    # Types
    path(
        'types/',
        views.ConfigurableTypesView.as_view(),
        name='configurable-types'
    ),
]
