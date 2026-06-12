"""App configuration for the core application."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core app providing landing pages and site-wide views."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
