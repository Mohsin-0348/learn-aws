"""
ASGI config for w3chat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# local imports
from .schema import MyGraphqlWsConsumer
from .middlewares import TokenMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'w3chat.settings')

django_asgi_app = get_asgi_application()

django.setup()

ws_patterns = [
    path('graphql/', MyGraphqlWsConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": TokenMiddleware(URLRouter(
        ws_patterns
    ))
})
