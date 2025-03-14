"""
ASGI config for corki project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from corki.config.ws_auth import WSAuthMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "corki.settings")
django.setup()

import corki.urls
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": WSAuthMiddleware(
        URLRouter(
            corki.urls.websocket_urlpatterns
        )
    )
})
