"""
WSGI config for Carbon Footprint Awareness Platform.

On Vercel: auto-runs migrate and collectstatic since /tmp is ephemeral.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_platform.settings')

application = get_wsgi_application()

# Vercel: auto-run migrations (SQLite in /tmp is wiped on cold starts)
if os.getenv('VERCEL'):
    from django.core.management import call_command
    import logging
    logger = logging.getLogger(__name__)
    try:
        call_command('migrate', '--run-syncdb', verbosity=0)
        logger.info('Vercel: migrations applied successfully.')
    except Exception as e:
        logger.warning(f'Vercel: migration failed: {e}')

app = application
