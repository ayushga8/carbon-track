"""Custom context processors for the core application."""

from django.conf import settings


def firebase_config(request):
    """Inject Firebase Web SDK configuration into every template context.

    Returns:
        dict: Firebase API key, auth domain, and project ID.
    """
    return {
        'firebase_api_key': getattr(settings, 'FIREBASE_WEB_API_KEY', ''),
        'firebase_auth_domain': getattr(settings, 'FIREBASE_AUTH_DOMAIN', ''),
        'firebase_project_id': getattr(settings, 'FIREBASE_PROJECT_ID', ''),
    }
