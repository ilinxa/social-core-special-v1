"""
User Admin Configuration
========================
Django admin configuration for User and UserProfile models.

Provides:
    - Custom UserAdmin extending Django's UserAdmin
    - Inline profile editing in User admin
    - Separate UserProfile admin for profile-only access
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from apps.users.models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile.

    Allows editing profile directly from User admin page.
    """
    model = UserProfile
    can_delete = False
    verbose_name = 'Profile'
    verbose_name_plural = 'Profile'
    fk_name = 'user'

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Preferences', {
            'fields': ('timezone', 'language')
        }),
        ('Media', {
            'fields': ('avatar',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.

    Features:
        - Email-based authentication (not username)
        - Inline profile editing
        - Custom list display and filters
        - Referral tracking
    """

    # Inline profile
    inlines = [UserProfileInline]

    # List view
    list_display = [
        'email',
        'username',
        'get_full_name_display',
        'is_active',
        'is_verified',
        'is_staff',
        'can_create_business',
        'date_joined',
        'referral_count',
    ]
    list_filter = [
        'is_active',
        'is_verified',
        'is_staff',
        'is_superuser',
        'can_create_business',
        'date_joined',
    ]
    search_fields = [
        'email',
        'username',
        'profile__first_name',
        'profile__last_name',
    ]
    ordering = ['-date_joined']
    list_per_page = 50

    # Detail view fieldsets
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Public Identity', {
            'fields': ('username',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'can_create_business')
        }),
        ('Permissions', {
            'fields': (
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Referral', {
            'fields': ('referred_by', 'get_referral_count')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )

    # Add user form (admin "Add User" page)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Optional', {
            'classes': ('wide', 'collapse'),
            'fields': ('username', 'is_staff', 'is_superuser'),
        }),
    )

    # Read-only fields
    readonly_fields = [
        'date_joined',
        'last_login',
        'created_at',
        'updated_at',
        'get_referral_count',
    ]

    # Filter horizontal for many-to-many
    filter_horizontal = ('groups', 'user_permissions',)

    # Custom display methods
    @admin.display(description='Full Name')
    def get_full_name_display(self, obj):
        """Display full name from profile."""
        if hasattr(obj, 'profile'):
            name = obj.profile.full_name
            if name != obj.email:
                return name
        return '-'

    @admin.display(description='Referrals')
    def referral_count(self, obj):
        """Display number of referrals."""
        count = obj.referrals.count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                count
            )
        return '0'

    @admin.display(description='Total Referrals')
    def get_referral_count(self, obj):
        """Detailed referral count for detail view."""
        return obj.referrals.count()

    def get_queryset(self, request):
        """Optimize queryset with profile prefetch."""
        return super().get_queryset(request).select_related('profile')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile model.

    Provides direct access to profiles without going through User admin.
    Useful for customer support to quickly update profile information.
    """

    list_display = [
        'get_user_email',
        'full_name',
        'phone',
        'timezone',
        'language',
        'has_avatar_display',
    ]
    list_filter = [
        'timezone',
        'language',
    ]
    search_fields = [
        'user__email',
        'first_name',
        'last_name',
        'phone',
    ]
    ordering = ['-user__date_joined']
    list_per_page = 50

    # Use raw_id_fields for user to avoid loading all users in dropdown
    raw_id_fields = ['user']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Media', {
            'fields': ('avatar',)
        }),
        ('Preferences', {
            'fields': ('timezone', 'language')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Email', ordering='user__email')
    def get_user_email(self, obj):
        """Display user email."""
        return obj.user.email

    @admin.display(description='Avatar', boolean=True)
    def has_avatar_display(self, obj):
        """Display avatar status as boolean icon."""
        return obj.has_avatar

    def get_queryset(self, request):
        """Optimize queryset with user select_related."""
        return super().get_queryset(request).select_related('user')
