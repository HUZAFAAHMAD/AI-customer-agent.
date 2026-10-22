"""
WSGI config for server project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

application = get_wsgi_application()

# Run background auto-seeding asynchronously so Gunicorn binds to port immediately
import threading

def _async_seed():
    try:
        import seed_kb
        seed_kb.auto_seed_knowledge_base()
    except Exception as e:
        print(f"Background seed notice: {e}")

threading.Thread(target=_async_seed, daemon=True).start()
