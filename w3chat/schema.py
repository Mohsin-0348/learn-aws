import graphene
import asyncio
import channels_graphql_ws

import users.schema as user_schema
import chat.schema as chat_schema


class Query(
    user_schema.Query,
    chat_schema.Query,
    graphene.ObjectType
):
    pass


class Mutation(
    user_schema.Mutation,
    chat_schema.Mutation,
    graphene.ObjectType
):
    pass


class Subscription(
    chat_schema.Subscription,
    graphene.ObjectType
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, subscription=Subscription)


def set_middleware(next, root, info, **args):
    return_value = next(root, info, **args)
    return return_value


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
    middleware = [set_middleware]
