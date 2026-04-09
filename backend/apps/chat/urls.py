"""
Chat URL Configuration
======================
All endpoints under /api/v1/chat/.
"""

from django.urls import path

from apps.chat import views

app_name = "chat"

urlpatterns = [
    # Conversations
    path(
        "conversations/",
        views.ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),
    path(
        "conversations/<uuid:conversation_id>/",
        views.ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    # Participants
    path(
        "conversations/<uuid:conversation_id>/participants/",
        views.ParticipantListAddView.as_view(),
        name="participant-list-add",
    ),
    path(
        "conversations/<uuid:conversation_id>/participants/<uuid:participant_id>/",
        views.ParticipantRemoveView.as_view(),
        name="participant-remove",
    ),
    path(
        "conversations/<uuid:conversation_id>/leave/",
        views.LeaveConversationView.as_view(),
        name="conversation-leave",
    ),
    # Messages
    path(
        "conversations/<uuid:conversation_id>/messages/",
        views.MessageListCreateView.as_view(),
        name="message-list-create",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages/<uuid:message_id>/",
        views.MessageEditDeleteView.as_view(),
        name="message-edit-delete",
    ),
    # Watermarks
    path(
        "conversations/<uuid:conversation_id>/seen/",
        views.MarkSeenView.as_view(),
        name="mark-seen",
    ),
    path(
        "conversations/<uuid:conversation_id>/mute/",
        views.MuteConversationView.as_view(),
        name="mute-conversation",
    ),
    path(
        "conversations/<uuid:conversation_id>/unmute/",
        views.UnmuteConversationView.as_view(),
        name="unmute-conversation",
    ),
    # Chat Requests
    path("requests/", views.ChatRequestListView.as_view(), name="request-list"),
    path(
        "requests/<uuid:conversation_id>/accept/",
        views.AcceptChatRequestView.as_view(),
        name="request-accept",
    ),
    path(
        "requests/<uuid:conversation_id>/ignore/",
        views.IgnoreChatRequestView.as_view(),
        name="request-ignore",
    ),
    # Blocks
    path("blocks/", views.BlockListCreateView.as_view(), name="block-list-create"),
    path(
        "blocks/<uuid:block_id>/",
        views.UnblockView.as_view(),
        name="unblock",
    ),
    # Unread counts
    path("unread/", views.UnreadCountsView.as_view(), name="unread-counts"),
    # Group Admin Management
    path(
        "conversations/<uuid:conversation_id>/participants/<uuid:participant_id>/promote/",
        views.PromoteToAdminView.as_view(),
        name="participant-promote",
    ),
    path(
        "conversations/<uuid:conversation_id>/participants/<uuid:participant_id>/demote/",
        views.DemoteFromAdminView.as_view(),
        name="participant-demote",
    ),
    # Attachments
    path(
        "conversations/<uuid:conversation_id>/upload/",
        views.AttachmentUploadView.as_view(),
        name="attachment-upload",
    ),
    # Media Gallery
    path(
        "conversations/<uuid:conversation_id>/media/",
        views.MediaGalleryView.as_view(),
        name="media-gallery",
    ),
    # Reactions
    path(
        "conversations/<uuid:conversation_id>/messages/<uuid:message_id>/reactions/",
        views.ReactionView.as_view(),
        name="message-reactions",
    ),
    # Entity Inbox
    path(
        "entity/<str:account_type>/<uuid:account_id>/inbox/",
        views.EntityInboxView.as_view(),
        name="entity-inbox",
    ),
    # Message Search
    path(
        "messages/search/",
        views.MessageSearchView.as_view(),
        name="message-search",
    ),
]
