"""Challenges app configuration."""

from django.apps import AppConfig


class ChallengesConfig(AppConfig):
    """Configuration for the Challenges application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'challenges'
    verbose_name = 'Eco Challenges'
