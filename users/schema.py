
import graphene

import users.mutation as user_mutation
import users.query as user_query


class Query(user_query.Query, graphene.ObjectType):
    """
        define all the queries together
    """
    pass


class Mutation(user_mutation.Mutation, graphene.ObjectType):
    """
        define all the mutations by identifier name for query
    """
    pass
