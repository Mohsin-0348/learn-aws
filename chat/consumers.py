import uuid

import channels_graphql_ws
from channels.db import database_sync_to_async

from chat.models import ConnectedParticipantConversation
from mysite.schema import schema


def delete_connection(user, token):
    ConnectedParticipantConversation.objects.filter(participant=user,
                                                    connection_token=token).delete()


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):
    schema = schema

    async def on_connect(self, payload):
        if self.scope["user"]:
            print(f"[connected]... <{self.scope['user']}>")
            self.scope['connection_token'] = uuid.uuid4()
        else:
            print("[connected]... AnonymousUser")

    async def disconnect(self, payload):
        await super(MyGraphqlWsConsumer, self).disconnect(payload)
        if self.scope["user"]:
            await database_sync_to_async(delete_connection)(self.scope["user"], self.scope["connection_token"])
            print("[Disconnected]...", f"<{self.scope['user']}>")
