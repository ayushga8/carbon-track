"""Calculator app configuration."""
from django.apps import AppConfig


class CalculatorConfig(AppConfig):
    """Configuration for the carbon footprint calculator app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calculator'
    verbose_name = 'Carbon Calculator'
