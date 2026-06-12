"""
ASGI config for Carbon Footprint Awareness Platform.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_platform.settings')

application = get_asgi_application()
