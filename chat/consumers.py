
import channels_graphql_ws

from mysite.schema import schema


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):

    schema = schema

    async def on_connect(self, payload):
        if self.scope["user"]:
            print(f"[connected]... <{self.scope['user']}>")
        else:
            print("[connected]... AnonymousUser")

    async def disconnect(self, payload):
        # await super(MyGraphqlWsConsumer, self).disconnect(payload)
        if self.scope["user"]:
            print("[Disconnected]...", f"<{self.scope['user']}>")
