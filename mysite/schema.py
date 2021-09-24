import graphene

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
