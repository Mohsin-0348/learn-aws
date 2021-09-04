"""
ASGI config for learn_pro project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

# local imports
from .schema import MyGraphqlWsConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learn_pro.settings')

ws_patterns = [
    path('graphql/', MyGraphqlWsConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(URLRouter(
        ws_patterns
    ))
})
