"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path, path

from chat import consumers
from .schema import MyGraphqlWsConsumer
from .middlewares import TokenMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

websocket_urlpatterns = [
    re_path(r'chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    path('graphql/', MyGraphqlWsConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(
            websocket_urlpatterns
        )
    ),
})
