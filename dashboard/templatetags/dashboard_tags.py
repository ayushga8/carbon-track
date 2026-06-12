"""Custom template tags and filters for the dashboard."""
from django import template

register = template.Library()


@register.filter
def carbon_format(value):
    """Format a float as carbon emission with unit."""
    try:
        return f"{float(value):.2f} kg CO₂"
    except (ValueError, TypeError):
        return "0.00 kg CO₂"


@register.filter
def carbon_color(value):
    """Return CSS class based on carbon amount."""
    try:
        val = float(value)
        if val < 5:
            return 'badge-easy'
        elif val < 20:
            return 'badge-medium'
        else:
            return 'badge-hard'
    except (ValueError, TypeError):
        return 'badge-easy'


@register.filter
def category_icon(category):
    """Return emoji icon for a category."""
    icons = {
        'transport': '🚗',
        'energy': '⚡',
        'food': '🍽️',
        'shopping': '🛍️',
        'waste': '🗑️',
        'general': '🌍',
    }
    return icons.get(category, '📊')


@register.filter
def category_display(category):
    """Return display name for a category."""
    names = {
        'transport': 'Transportation',
        'energy': 'Home Energy',
        'food': 'Food & Diet',
        'shopping': 'Shopping',
        'waste': 'Waste',
        'general': 'General',
    }
    return names.get(category, category.title())
