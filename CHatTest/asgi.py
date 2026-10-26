"""
ASGI config for CHatTest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter,URLRouter
from main import routing
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CHatTest.settings')


application = ProtocolTypeRouter (
    {
        'http': get_asgi_application(),
        'websocket':AuthMiddlewareStack(URLRouter(routing.ASGI_urlpatterns))
    }
)
