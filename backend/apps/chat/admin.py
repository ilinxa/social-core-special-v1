from django.contrib import admin

from apps.chat.models import ChatBlock, Conversation, ConversationParticipant, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation_type",
        "scope_type",
        "name",
        "is_active",
        "created_at",
    )
    list_filter = ("conversation_type", "scope_type", "is_active")
    search_fields = ("name", "id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "participant_type",
        "participant_id",
        "role",
        "request_status",
        "is_active",
    )
    list_filter = ("participant_type", "role", "request_status", "is_active")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("conversation", "removed_by", "added_by")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender_type",
        "sender_id",
        "content_type",
        "sequence_number",
        "status",
        "created_at",
    )
    list_filter = ("content_type", "status", "sender_type")
    search_fields = ("content",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("conversation",)


@admin.register(ChatBlock)
class ChatBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked_type", "blocked_id", "created_at")
    list_filter = ("blocked_type",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("blocker",)
