
import django.contrib.auth
import graphene
from graphene_django.types import DjangoObjectType

# local imports
from chat.filters import (
    ClientOffensiveWordFilters,
    ClientREFormatFilters,
    ConversationFilters,
    FavoriteMessageFilters,
    MessageFilters,
    OffensiveWordFilters,
    ParticipantFilters,
    REFormatFilters,
)
from chat.models import (
    ChatMessage,
    ClientOffensiveWords,
    ClientREFormats,
    Conversation,
    FavoriteMessage,
    OffensiveWord,
    Participant,
    REFormat,
)
from mysite.count_connection import CountConnection

User = django.contrib.auth.get_user_model()


class ParticipantType(DjangoObjectType):
    """
        define django object type for chat model
    """
    object_id = graphene.ID()
    unread_count = graphene.Int()
    is_online = graphene.Boolean()

    class Meta:
        model = Participant
        filterset_class = ParticipantFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk

    @staticmethod
    def resolve_unread_count(self, info, **kwargs):
        return self.unread_count

    @staticmethod
    def resolve_is_online(self, info, **kwargs):
        return self.is_online


class MessageType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()
    status = graphene.String()
    receiver = graphene.Field(ParticipantType)
    is_favorite = graphene.Boolean()

    class Meta:
        model = ChatMessage
        filterset_class = MessageFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk

    @staticmethod
    def resolve_status(self, info, **kwargs):
        return self.status

    @staticmethod
    def resolve_receiver(self, info, **kwargs):
        return self.receiver

    @staticmethod
    def resolve_is_favorite(self, info, **kwargs):
        return self.is_favorite(user=info.context.user)


class ConversationType(DjangoObjectType):
    """
        define django object type for chat model
    """
    object_id = graphene.ID()
    last_message = graphene.Field(MessageType)
    opposite_user = graphene.Field(ParticipantType)
    unread_count = graphene.Int()

    class Meta:
        model = Conversation
        filterset_class = ConversationFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk

    @staticmethod
    def resolve_last_message(self, info, **kwargs):
        return self.last_message

    @staticmethod
    def resolve_opposite_user(self, info, **kwargs):
        participant = info.context.user
        return self.opposite_user(participant)

    @staticmethod
    def resolve_unread_count(self, info, **kwargs):
        participant = info.context.user
        return self.unread_count(participant)


class FavoriteMessageType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = FavoriteMessage
        filterset_class = FavoriteMessageFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class OffensiveWordType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = OffensiveWord
        filterset_class = OffensiveWordFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class ClientOffensiveWordsType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = ClientOffensiveWords
        filterset_class = ClientOffensiveWordFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class REFormatType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = REFormat
        filterset_class = REFormatFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class ClientREFormatsType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = ClientREFormats
        filterset_class = ClientREFormatFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk
