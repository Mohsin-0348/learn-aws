
import graphene

import chat.mutation as chat_mutation
import chat.query as chat_query
import chat.subscription as chat_subscription


class Query(chat_query.Query, graphene.ObjectType):
    """
        define all the queries together
    """
    pass


class Mutation(chat_mutation.Mutation, graphene.ObjectType):
    """
        define all the mutations by identifier name for query
    """
    pass


class Subscription(chat_subscription.Subscription, graphene.ObjectType):
    """Root GraphQL subscription."""
    pass
