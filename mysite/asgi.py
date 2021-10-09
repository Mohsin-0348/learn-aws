"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from chat import consumers
from chat.models import Participant
from mysite.middlewares import TokenMiddleware

if Participant.objects.all():
    Participant.objects.update(count_connection=0)

websocket_urlpatterns = [
    # re_path(r'chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    path('graphql/', consumers.MyGraphqlWsConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenMiddleware(URLRouter(
        websocket_urlpatterns
    )
    ),
})
