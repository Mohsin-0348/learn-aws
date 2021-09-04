
"""All Schema Will Collect here,
     it is master schema file"""


import graphene
import channels_graphql_ws

import content.schema as content_schema


class Query(
    content_schema.Query,
    graphene.ObjectType
):
    """All query will in include this class"""
    pass


class Mutation(
    content_schema.Mutation,
    graphene.ObjectType
):
    pass


# class Subscription(
#     graphene.ObjectType,
#     content_schema.Subscription
# ):
#     """Root GraphQL subscription."""
#     pass


schema = graphene.Schema(query=Query, mutation=Mutation, subscription=content_schema.Subscription)


def set_middleware(next, root, info, **args):
    return_value = next(root, info, **args)
    return return_value


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):

    async def on_connect(self, payload):
        print("[connected]...")

    async def disconnect(self, payload):
        print("[Disconnected]...")

    schema = schema
    middleware = [set_middleware]
