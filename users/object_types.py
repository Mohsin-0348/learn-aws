
import graphene
from django.contrib.auth import get_user_model
from graphene_django import DjangoObjectType

from mysite.count_connection import CountConnection
from users.filters import ClientFilters, LogsFilters, UserFilters
from users.models import Client, UnitOfHistory

User = get_user_model()


class UserType(DjangoObjectType):
    object_id = graphene.ID()

    class Meta:
        model = User
        filterset_class = UserFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class LogType(DjangoObjectType):
    object_id = graphene.ID()

    class Meta:
        model = UnitOfHistory
        filterset_class = LogsFilters
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class ClientType(DjangoObjectType):
    object_id = graphene.ID()

    class Meta:
        model = Client
        filterset_class = ClientFilters
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk
