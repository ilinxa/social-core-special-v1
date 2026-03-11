"""
Audit Log Model
===============
Immutable audit log entry for compliance-grade tracking.

Design principles:
    - Append-only (no update/delete)
    - Self-contained (stores snapshot, not references)
    - Indexed for compliance queries

Usage:
    from apps.core.observability.audit import AuditLog, AuditService

    AuditService.log(
        action=AuditLog.Action.LOGIN_SUCCESS,
        actor=user,
        resource=session,
        request=request,
    )
"""

import uuid
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit log entry.

    Records WHO did WHAT, WHEN, WHERE, and WHY for compliance
    and security tracking. Entries cannot be modified or deleted.
    """

    class Action(models.TextChoices):
        """
        Audit action types.
        Format: {domain}.{resource}.{action}
        """
        # Authentication
        LOGIN_SUCCESS = "auth.login.success", "Login Success"
        LOGIN_FAILED = "auth.login.failed", "Login Failed"
        LOGOUT = "auth.logout", "Logout"
        TOKEN_REFRESH = "auth.token.refresh", "Token Refresh"

        # Password
        PASSWORD_CHANGED = "auth.password.changed", "Password Changed"
        PASSWORD_RESET_REQUESTED = "auth.password.reset_requested", "Password Reset Requested"
        PASSWORD_RESET_COMPLETED = "auth.password.reset_completed", "Password Reset Completed"

        # Email Verification
        VERIFICATION_SENT = "auth.verification.sent", "Verification Sent"
        EMAIL_VERIFIED = "auth.email.verified", "Email Verified"
        EMAIL_UNVERIFIED = "auth.email.unverified", "Email Unverified"

        # OAuth
        OAUTH_LINKED = "auth.oauth.linked", "OAuth Account Linked"
        OAUTH_UNLINKED = "auth.oauth.unlinked", "OAuth Account Unlinked"

        # Sessions
        SESSION_CREATED = "auth.session.created", "Session Created"
        SESSION_REVOKED = "auth.session.revoked", "Session Revoked"
        ALL_SESSIONS_REVOKED = "auth.sessions.revoked_all", "All Sessions Revoked"

        # User Management
        USER_CREATED = "user.created", "User Created"
        USER_UPDATED = "user.updated", "User Updated"
        USER_DEACTIVATED = "user.deactivated", "User Deactivated"
        USER_REACTIVATED = "user.reactivated", "User Reactivated"
        USER_DELETED = "user.deleted", "User Deleted"

        # Profile
        PROFILE_UPDATED = "user.profile.updated", "Profile Updated"
        AVATAR_CHANGED = "user.avatar.changed", "Avatar Changed"
        AVATAR_DELETED = "user.avatar.deleted", "Avatar Deleted"
        COVER_IMAGE_CHANGED = "user.cover_image.changed", "Cover Image Changed"
        COVER_IMAGE_DELETED = "user.cover_image.deleted", "Cover Image Deleted"

        # Notifications
        NOTIFICATION_PREFERENCE_UPDATED = "notification.preference.updated", "Notification Preference Updated"

        # Email Templates (Admin)
        EMAIL_TEMPLATE_CREATED = "email.template.created", "Email Template Created"
        EMAIL_TEMPLATE_UPDATED = "email.template.updated", "Email Template Updated"

        # Administrative
        ADMIN_USER_UPDATED = "admin.user.updated", "Admin Updated User"
        ADMIN_USER_DEACTIVATED = "admin.user.deactivated", "Admin Deactivated User"
        ADMIN_SETTINGS_CHANGED = "admin.settings.changed", "Admin Changed Settings"

        # Data Export/Access
        DATA_EXPORTED = "data.exported", "Data Exported"
        SENSITIVE_DATA_ACCESSED = "data.sensitive.accessed", "Sensitive Data Accessed"

        # Organization - Platform
        PLATFORM_CONFIGURED = "org.platform.configured", "Platform Configured"
        PLATFORM_SETTINGS_UPDATED = "org.platform.settings_updated", "Platform Settings Updated"
        PLATFORM_PROFILE_UPDATED = "org.platform.profile_updated", "Platform Profile Updated"

        # Organization - Business
        BUSINESS_CREATED = "org.business.created", "Business Created"
        BUSINESS_UPDATED = "org.business.updated", "Business Updated"
        BUSINESS_SUSPENDED = "org.business.suspended", "Business Suspended"
        BUSINESS_REACTIVATED = "org.business.reactivated", "Business Reactivated"
        BUSINESS_ARCHIVED = "org.business.archived", "Business Archived"
        BUSINESS_DELETED = "org.business.deleted", "Business Deleted"
        BUSINESS_SLUG_CHANGED = "org.business.slug_changed", "Business Slug Changed"
        BUSINESS_PROFILE_UPDATED = "org.business.profile_updated", "Business Profile Updated"
        BUSINESS_CREATION_PERMISSION_GRANTED = "org.business.creation_permission_granted", "Business Creation Permission Granted"

        # Organization - Verification
        VERIFICATION_APPROVED = "org.verification.approved", "Verification Approved"
        VERIFICATION_REJECTED = "org.verification.rejected", "Verification Rejected"

        # Organization - Ownership
        # NOTE: Ownership transfer has a 3-stage audit trail:
        # 1. OWNERSHIP_TRANSFER_INITIATED (Organization system) - When transaction created
        # 2. OWNERSHIP_TRANSFERRED (RBAC system) - When transaction accepted
        # 3. OWNER_MEMBERSHIP_CREATED (RBAC system) - When new owner membership created
        OWNERSHIP_TRANSFER_INITIATED = "org.ownership.transfer_initiated", "Ownership Transfer Initiated"

        # RBAC - Roles
        ROLE_CREATED = "rbac.role.created", "Role Created"
        ROLE_UPDATED = "rbac.role.updated", "Role Updated"
        ROLE_DELETED = "rbac.role.deleted", "Role Deleted"
        ROLE_PERMISSION_ADDED = "rbac.role.permission_added", "Permission Added to Role"
        ROLE_PERMISSION_REMOVED = "rbac.role.permission_removed", "Permission Removed from Role"

        # RBAC - Membership
        MEMBERSHIP_CREATED = "rbac.membership.created", "Membership Created"
        MEMBERSHIP_UPDATED = "rbac.membership.updated", "Membership Updated"
        MEMBERSHIP_ROLE_CHANGED = "rbac.membership.role_changed", "Member Role Changed"
        MEMBERSHIP_SUSPENDED = "rbac.membership.suspended", "Member Suspended"
        MEMBERSHIP_REACTIVATED = "rbac.membership.reactivated", "Member Reactivated"
        MEMBERSHIP_REMOVED = "rbac.membership.removed", "Member Removed"
        MEMBERSHIP_BANNED = "rbac.membership.banned", "Member Banned"
        MEMBERSHIP_LEFT = "rbac.membership.left", "Member Left"
        MEMBERSHIP_RESTORED = "rbac.membership.restored", "Member Restored"

        # RBAC - Ownership
        OWNERSHIP_TRANSFERRED = "rbac.ownership.transferred", "Ownership Transferred"
        OWNER_MEMBERSHIP_CREATED = "rbac.owner.created", "Owner Membership Created"

        # Transaction System
        TRANSACTION_CREATED = "txn.created", "Transaction Created"
        TRANSACTION_ACCEPTED = "txn.accepted", "Transaction Accepted"
        TRANSACTION_DENIED = "txn.denied", "Transaction Denied"
        TRANSACTION_DISMISSED = "txn.dismissed", "Transaction Dismissed"
        TRANSACTION_CANCELLED = "txn.cancelled", "Transaction Cancelled"
        TRANSACTION_EXPIRED = "txn.expired", "Transaction Expired"
        TRANSACTION_INVALIDATED = "txn.invalidated", "Transaction Invalidated"
        TRANSACTION_INFO_REQUESTED = "txn.info_requested", "Transaction Info Requested"
        TRANSACTION_RESUBMITTED = "txn.resubmitted", "Transaction Resubmitted"
        TRANSACTION_PENDING_REVIEW = "txn.pending_review", "Transaction Pending Review"
        TRANSACTION_REVIEW_APPROVED = "txn.review_approved", "Transaction Review Approved"

        # Forms - Templates
        FORM_TEMPLATE_CREATED = "forms.template.created", "Form Template Created"
        FORM_TEMPLATE_UPDATED = "forms.template.updated", "Form Template Updated"
        FORM_TEMPLATE_PUBLISHED = "forms.template.published", "Form Template Published"
        FORM_TEMPLATE_ARCHIVED = "forms.template.archived", "Form Template Archived"
        FORM_TEMPLATE_DELETED = "forms.template.deleted", "Form Template Deleted"
        FORM_TEMPLATE_VERSIONED = "forms.template.versioned", "Form Template Versioned"
        FORM_TEMPLATE_FORKED = "forms.template.forked", "Form Template Forked"

        # Forms - Fields
        FORM_FIELD_ADDED = "forms.field.added", "Form Field Added"
        FORM_FIELD_UPDATED = "forms.field.updated", "Form Field Updated"
        FORM_FIELD_REMOVED = "forms.field.removed", "Form Field Removed"

        # Forms - Responses
        FORM_RESPONSE_CREATED = "forms.response.created", "Form Response Created"
        FORM_RESPONSE_UPDATED = "forms.response.updated", "Form Response Updated"
        FORM_RESPONSE_SUBMITTED = "forms.response.submitted", "Form Response Submitted"
        FORM_RESPONSE_PROCESSED = "forms.response.processed", "Form Response Processed"
        FORM_RESPONSE_VOIDED = "forms.response.voided", "Form Response Voided"
        FORM_RESPONSE_EXPORTED = "forms.response.exported", "Form Responses Exported"

        # CMS - Sites
        CMS_SITE_CREATED = "cms.site.created", "CMS Site Created"
        CMS_SITE_UPDATED = "cms.site.updated", "CMS Site Updated"
        CMS_SITE_DELETED = "cms.site.deleted", "CMS Site Deleted"

        # CMS - Pages
        CMS_PAGE_CREATED = "cms.page.created", "CMS Page Created"
        CMS_PAGE_UPDATED = "cms.page.updated", "CMS Page Updated"
        CMS_PAGE_DELETED = "cms.page.deleted", "CMS Page Deleted"
        CMS_PAGE_PUBLISHED = "cms.page.published", "CMS Page Published"
        CMS_PAGE_UNPUBLISHED = "cms.page.unpublished", "CMS Page Unpublished"
        CMS_PAGE_ARCHIVED = "cms.page.archived", "CMS Page Archived"

        # CMS - Templates
        CMS_SECTION_TEMPLATE_CREATED = "cms.section_template.created", "Section Template Created"
        CMS_SECTION_TEMPLATE_UPDATED = "cms.section_template.updated", "Section Template Updated"
        CMS_SECTION_TEMPLATE_DELETED = "cms.section_template.deleted", "Section Template Deleted"
        CMS_BLOCK_TEMPLATE_CREATED = "cms.block_template.created", "Block Template Created"
        CMS_BLOCK_TEMPLATE_UPDATED = "cms.block_template.updated", "Block Template Updated"
        CMS_BLOCK_TEMPLATE_DELETED = "cms.block_template.deleted", "Block Template Deleted"
        CMS_BLOCK_SCHEMA_CHANGED = "cms.block_template.schema_changed", "Block Schema Changed"

        # CMS - Content
        CMS_CONTENT_DRAFT_SAVED = "cms.content.draft_saved", "CMS Content Draft Saved"
        CMS_CONTENT_ROLLBACK = "cms.content.rollback", "CMS Content Rolled Back"
        CMS_VISIBILITY_TOGGLED = "cms.placement.visibility_toggled", "CMS Visibility Toggled"

        # CMS - Media
        CMS_MEDIA_UPLOADED = "cms.media.uploaded", "CMS Media Uploaded"
        CMS_MEDIA_UPDATED = "cms.media.updated", "CMS Media Updated"
        CMS_MEDIA_DELETED = "cms.media.deleted", "CMS Media Deleted"
        CMS_MEDIA_TOMBSTONED = "cms.media.tombstoned", "CMS Media Tombstoned"

        # CMS - Import/Export
        CMS_PAGE_EXPORTED = "cms.page.exported", "CMS Page Exported"
        CMS_PAGE_IMPORTED = "cms.page.imported", "CMS Page Imported"

        # CMS - API Keys
        CMS_API_KEY_CREATED = "cms.api_key.created", "CMS API Key Created"
        CMS_API_KEY_REVOKED = "cms.api_key.revoked", "CMS API Key Revoked"
        CMS_API_KEY_UPDATED = "cms.api_key.updated", "CMS API Key Updated"

        # Network
        FOLLOW_CREATED = "network.follow.created", "Follow Created"
        FOLLOW_REMOVED = "network.follow.removed", "Follow Removed"
        FOLLOWER_REMOVED = "network.follower.removed", "Follower Removed"
        CONNECTION_CREATED = "network.connection.created", "Connection Created"
        CONNECTION_DISCONNECTED = "network.connection.disconnected", "Connection Disconnected"

    class ActorType(models.TextChoices):
        """Type of actor performing the action."""
        USER = "user", "User"
        ADMIN = "admin", "Administrator"
        SYSTEM = "system", "System"
        ANONYMOUS = "anonymous", "Anonymous"

    class Outcome(models.TextChoices):
        """Outcome of the action."""
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Permission Denied"

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Timestamp (immutable)
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred",
    )

    # Actor information (WHO)
    # Stored as snapshot, not FK - actor may be deleted later
    # CharField to support both integer and UUID primary keys
    actor_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the actor (user ID as string)",
    )
    actor_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email snapshot at time of action",
    )
    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
        default=ActorType.USER,
        help_text="Type of actor",
    )

    # Action information (WHAT)
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
        help_text="Action performed",
    )

    # Resource information (ON WHAT)
    resource_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Type of resource affected (e.g., 'User', 'DeviceSession')",
    )
    # CharField to support both integer and UUID primary keys
    resource_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of affected resource (as string)",
    )
    resource_repr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable resource representation",
    )

    # Request context (WHERE/HOW)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text="Client user agent string",
    )
    request_id = models.CharField(
        max_length=36,
        blank=True,
        default="",
        db_index=True,
        help_text="Correlation ID for request tracing",
    )

    # Outcome
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        default=Outcome.SUCCESS,
        db_index=True,
        help_text="Action outcome",
    )

    # Additional details (WHY/CONTEXT)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured details",
    )

    # Change tracking (for updates)
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Before/after values for updates",
    )

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

        indexes = [
            # Composite index for common queries
            models.Index(
                fields=["actor_id", "-timestamp"],
                name="audit_actor_time_idx",
            ),
            models.Index(
                fields=["action", "-timestamp"],
                name="audit_action_time_idx",
            ),
            models.Index(
                fields=["resource_type", "resource_id"],
                name="audit_resource_idx",
            ),
            # Date-based partitioning helper
            models.Index(
                fields=["-timestamp"],
                name="audit_timestamp_idx",
            ),
        ]

    def __str__(self):
        return f"{self.timestamp} | {self.actor_email or self.actor_type} | {self.action}"

    def save(self, *args, **kwargs):
        """Enforce append-only behavior."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog entries cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        raise ValueError("AuditLog entries cannot be deleted")
