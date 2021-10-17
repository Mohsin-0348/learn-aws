import asyncio
import json

import channels_graphql_ws
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone

from chat.models import ChatMessage, Conversation
from chat.schema import ChatSubscription, MessageSubscription
from mysite.schema import schema


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))


def deliver_message(user):
    messages = ChatMessage.objects.filter(
        conversation__participants=user, is_delivered=False, is_read=False, is_deleted=False
    ).exclude(sender=user)
    for msg in messages:
        msg.is_delivered = True
        msg.delivered_on = timezone.now()
        msg.save()
        if msg == msg.conversation.last_message and msg.sender.is_online:
            ChatSubscription.broadcast(payload=msg.conversation, group=str(msg.sender.id))
        if msg.sender in msg.conversation.connected.all():
            MessageSubscription.broadcast(payload=msg, group=str(msg.conversation.id))


def send_data(user):
    for chat in Conversation.objects.filter(participants=user):
        if chat.opposite_user(user).is_online:
            ChatSubscription.broadcast(payload=chat, group=str(chat.opposite_user(user).id))


def online_status_update(user, connected=False, chat_id=None):
    if connected:
        if user.count_connection > 0:
            user.count_connection -= 1
            if user.count_connection == 0:
                user.is_online = False
            user.save()
        else:
            user.is_online = False
            user.save()
        send_data(user)
    if chat_id:
        Conversation.objects.get(id=chat_id, participants=user).connected.remove(user)


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):

    async def on_connect(self, payload):
        if not self.scope["user"] or self.scope['path'] != '/graphql/':
            await self.disconnect(payload)
        else:
            self.scope["chats"] = ""
            self.scope["chat_connection"] = None
            print("[connected]...", f"<{self.scope['user']}>")
            await asyncio.get_event_loop().run_in_executor(
                None, send_data, self.scope["user"]
            )
            await asyncio.get_event_loop().run_in_executor(
                None, deliver_message, self.scope["user"]
            )

    async def disconnect(self, payload):
        if self.scope["user"]:
            chat_connection = False
            if self.scope["chat_connection"]:
                chat_connection = True
            if self.scope['chats']:
                await asyncio.get_event_loop().run_in_executor(
                    None, online_status_update, self.scope["user"], chat_connection, self.scope['chats']
                )
            await asyncio.get_event_loop().run_in_executor(
                None, online_status_update, self.scope["user"], chat_connection
            )
            print("[Disconnected]...", f"<{self.scope['user']}>")

    # async def unsubscribe(self, message):
    #     print(True)
    #     print(message)
    #     print(self.scope)
    #     # if self.scope["user"]:
    #     #     chat_connection = False
    #     #     if self.scope["chat_connection"]:
    #     #         chat_connection = True
    #     #     if self.scope['chats']:
    #     #         await asyncio.get_event_loop().run_in_executor(
    #     #             None, online_status_update, self.scope["user"], chat_connection, self.scope['chats']
    #     #         )
    #     #     await asyncio.get_event_loop().run_in_executor(
    #     #         None, online_status_update, self.scope["user"], chat_connection
    #     #     )
    #     #     print("[Unsubscribed]...", f"<{self.scope['user'].id}>")

    schema = schema
