# apps/network/admin.py
from django.contrib import admin
from apps.network.models import Follow, Connection


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "followee_type", "followee_id", "status", "created_at")
    list_filter = ("status", "followee_type")
    search_fields = ("follower__email",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("follower", "removed_by")


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ("connection_type", "user_a", "user_b", "status", "connected_at")
    list_filter = ("connection_type", "status")
    search_fields = ("user_a__email", "user_b__email")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user_a", "user_b", "initiated_by", "disconnected_by")
