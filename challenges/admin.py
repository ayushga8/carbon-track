"""Admin configuration for the Challenges application."""

from django.contrib import admin

from .models import Challenge, UserChallenge


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    """Admin interface for Challenge model."""

    list_display = [
        'title', 'category', 'difficulty', 'carbon_save_potential',
        'duration_days', 'participants_count', 'is_active', 'created_at',
    ]
    list_filter = ['category', 'difficulty', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    ordering = ['-created_at']


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    """Admin interface for UserChallenge model."""

    list_display = [
        'user', 'challenge', 'status', 'progress',
        'started_at', 'completed_at',
    ]
    list_filter = ['status', 'challenge__category']
    search_fields = ['user__username', 'challenge__title']
    raw_id_fields = ['user', 'challenge']
    ordering = ['-started_at']
