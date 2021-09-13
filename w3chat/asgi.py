"""
ASGI config for w3chat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

# local imports
from .schema import MyGraphqlWsConsumer
from .middlewares import TokenMiddleware

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'w3chat.settings')

ws_patterns = [
    path('graphql/', MyGraphqlWsConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": TokenMiddleware(URLRouter(
        ws_patterns
    ))
})
