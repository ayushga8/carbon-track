"""Admin configuration for the accounts app."""

from django.contrib import admin
from django.utils.html import format_html

from .models import UserProfile, EmailOTP


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""

    list_display = [
        'user',
        'auth_provider',
        'is_email_verified',
        'total_carbon_saved',
        'location',
        'created_at',
    ]
    list_filter = ['auth_provider', 'is_email_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'location', 'bio']
    readonly_fields = ['created_at', 'firebase_uid']
    raw_id_fields = ['user']

    fieldsets = (
        ('User Info', {
            'fields': ('user', 'avatar', 'bio', 'location'),
        }),
        ('Authentication', {
            'fields': ('auth_provider', 'firebase_uid', 'is_email_verified'),
        }),
        ('Stats', {
            'fields': ('total_carbon_saved',),
        }),
        ('Dates', {
            'fields': ('created_at',),
        }),
    )


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """Admin configuration for EmailOTP model."""

    list_display = [
        'user',
        'otp_code',
        'created_at',
        'expires_at',
        'is_used',
        'attempts',
        'otp_status',
    ]
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['otp_code', 'created_at', 'expires_at']
    raw_id_fields = ['user']

    def otp_status(self, obj):
        """Display OTP validity status with color coding."""
        if obj.is_valid():
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Valid</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Expired</span>'
        )
    otp_status.short_description = 'Status'
