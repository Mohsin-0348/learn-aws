
import graphene
from django.contrib.auth import get_user_model
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError

from mysite.permissions import is_admin_user, is_authenticated
from users.models import Client, UnitOfHistory
from users.object_types import ClientType, LogType, UserType

User = get_user_model()


class Query(graphene.ObjectType):
    users = DjangoFilterConnectionField(UserType)
    user = graphene.relay.Node.Field(UserType)
    logs = DjangoFilterConnectionField(LogType)
    log = graphene.relay.Node.Field(LogType)
    clients = DjangoFilterConnectionField(ClientType)
    client = graphene.relay.Node.Field(ClientType)
    me = graphene.Field(UserType)

    @is_authenticated
    def resolve_me(self, info, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError(
                message='Your are not login',
                extensions={
                    "message": "Your are not login",
                    "code": "unauthorised"
                })
        return user

    @is_admin_user
    def resolve_users(self, info, **kwargs):
        return User.objects.all()

    @is_admin_user
    def resolve_clients(self, info, **kwargs):
        return Client.objects.all()

    @is_admin_user
    def resolve_logs(self, info, **kwargs):
        return UnitOfHistory.objects.all()
