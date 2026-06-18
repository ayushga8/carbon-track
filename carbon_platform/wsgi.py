"""
WSGI config for Carbon Footprint Awareness Platform.

Includes Vercel build hook: runs collectstatic on first import
so WhiteNoise can serve static files in serverless environment.
"""

import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_platform.settings')

application = get_wsgi_application()

# Vercel build hook: collect static files if staticfiles dir is missing
_staticfiles_dir = Path(__file__).resolve().parent.parent / 'staticfiles'
if not _staticfiles_dir.exists():
    import subprocess
    import sys
    subprocess.run(
        [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
        check=False,
    )

app = application
