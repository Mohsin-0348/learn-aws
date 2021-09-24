
import json
import asyncio
import channels_graphql_ws
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
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


def online_status_update(user, is_online=False):
    user.is_online = is_online
    user.save()


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):

    async def on_connect(self, payload):
        if not self.scope["user"]:
            await self.disconnect(payload)
        else:
            print("[connected]...", f"<{self.scope['user'].id}>")
            await asyncio.get_event_loop().run_in_executor(None, online_status_update, self.scope["user"], True)

    async def disconnect(self, payload):
        if self.scope["user"]:
            await asyncio.get_event_loop().run_in_executor(None, online_status_update, self.scope["user"])
            print("[Disconnected]...", f"<{self.scope['user'].id}>")

    schema = schema
