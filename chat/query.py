
import django.contrib.auth
import graphene
from django.db.models import Q
from django.utils import timezone
from graphene_django.filter.fields import DjangoFilterConnectionField

# local imports
from chat.models import (
    ChatMessage,
    ClientOffensiveWords,
    ClientREFormats,
    Conversation,
    FavoriteMessage,
    OffensiveWord,
    REFormat,
)
from chat.object_types import (
    ConversationType,
    MessageType,
    OffensiveWordType,
    ParticipantType,
    REFormatType,
)
from chat.subscription import (
    ChatSubscription,
    MessageCountSubscription,
    MessageSubscription,
    TypingSubscription,
)
from mysite.permissions import is_admin_user, is_authenticated, is_client_request
from users.models import Client

User = django.contrib.auth.get_user_model()


class ConversationQuery(graphene.ObjectType):
    """
        query all chat information
    """
    conversation = graphene.Field(ConversationType, id=graphene.ID())
    conversations = DjangoFilterConnectionField(ConversationType)
    user_conversation = graphene.Field(ConversationType, id=graphene.ID())
    user_conversations = DjangoFilterConnectionField(ConversationType)

    @is_authenticated
    def resolve_conversation(self, info, id, **kwargs):
        user = info.context.user
        if user.is_admin:
            conversation = Conversation.objects.get(id=id)
        else:
            conversation = Conversation.objects.get(Q(client__admin=user) | Q(client__employee=user), id=id)
        return conversation

    @is_authenticated
    def resolve_conversations(self, info, **kwargs):
        user = info.context.user
        if user.is_admin:
            objects = Conversation.objects.all()
        else:
            objects = Conversation.objects.filter(Q(client__admin=user) | Q(client__employee=user))
        return objects

    @is_client_request
    def resolve_user_conversation(self, info, id, **kwargs):
        participant = info.context.user
        conversation = Conversation.objects.get(id=id, participants=participant)
        return conversation

    @is_client_request
    def resolve_user_conversations(self, info, **kwargs):
        participant = info.context.user
        objects = Conversation.objects.filter(participants=participant)
        return objects


class MessageQuery(graphene.ObjectType):
    """
        query all messages information for admin panel
    """
    all_messages = DjangoFilterConnectionField(MessageType)
    user_conversation_messages = DjangoFilterConnectionField(MessageType, chat_id=graphene.ID())
    user_favorite_messages = DjangoFilterConnectionField(MessageType)
    message_info = graphene.Field(MessageType, id=graphene.ID())
    message_count = graphene.Int()

    @is_admin_user
    def resolve_all_messages(self, info, **kwargs):
        return ChatMessage.objects.all().select_related("sender", 'conversation')

    @is_client_request
    def resolve_message_info(self, info, id, **kwargs):
        return ChatMessage.objects.get(id=id, conversation__participants=info.context.user)

    @is_client_request
    def resolve_user_conversation_messages(self, info, chat_id, **kwargs):
        participant = info.context.user
        conversation = Conversation.objects.get(id=chat_id, participants=participant)
        unread_messages = conversation.messages.filter(is_read=False, is_deleted=False).exclude(sender=participant)
        message_data = [obj.id for obj in unread_messages]
        if unread_messages:
            unread_messages.update(is_read=True, read_on=timezone.now())
            for msg in ChatMessage.objects.filter(id__in=message_data):
                MessageSubscription.broadcast(payload=msg, group=str(conversation.id))
            ChatSubscription.broadcast(payload=conversation, group=str(participant.id))
            MessageCountSubscription.broadcast(payload=participant.unread_count, group=str(participant.id))
        return ChatMessage.objects.filter(conversation=conversation).exclude(
            deleted_from=participant).select_related("sender", 'conversation')

    @is_client_request
    def resolve_user_favorite_messages(self, info, **kwargs):
        user = info.context.user
        user_fav, created = FavoriteMessage.objects.get_or_create(participant=user)
        return user_fav.messages.exclude(deleted_from=user).select_related("sender", 'conversation')

    @is_client_request
    def resolve_message_count(self, info, **kwargs):
        return info.context.user.unread_count


class Query(ConversationQuery, MessageQuery, graphene.ObjectType):
    """
        define all the queries together
    """
    participant_user = graphene.Field(ParticipantType)
    offensive_words = DjangoFilterConnectionField(OffensiveWordType)
    re_formats = DjangoFilterConnectionField(REFormatType)
    message_typing = graphene.Boolean(chat_id=graphene.ID())

    @is_client_request
    def resolve_participant_user(self, info, **kwargs):
        return info.context.user

    @is_client_request
    def resolve_message_typing(self, info, chat_id, **kwargs):
        user = info.context.user
        conversation = Conversation.objects.get(id=chat_id)
        TypingSubscription.broadcast(
            payload=True, group=(str(conversation.id) + str(conversation.opposite_user(user).id))
        )
        return True

    @is_authenticated
    def resolve_offensive_words(self, info, **kwargs):
        user = info.context.user
        words = OffensiveWord.objects.filter(id=0)
        if user.is_admin:
            words = OffensiveWord.objects.all()
        elif Client.objects.filter(admin=user):
            client = Client.objects.filter(admin=user).last()
            if ClientOffensiveWords.objects.filter(client=client):
                words = ClientOffensiveWords.objects.filter(client=client).last().words.all()
        elif Client.objects.filter(employee=user):
            client = Client.objects.filter(employee=user).last()
            if ClientOffensiveWords.objects.filter(client=client):
                words = ClientOffensiveWords.objects.filter(client=client).last().words.all()

        return words

    @is_authenticated
    def resolve_re_formats(self, info, **kwargs):
        user = info.context.user
        expressions = REFormat.objects.filter(id=0)
        if user.is_admin:
            expressions = REFormat.objects.all()
        elif Client.objects.filter(admin=user):
            client = Client.objects.filter(admin=user).last()
            if ClientREFormats.objects.filter(client=client):
                expressions = ClientREFormats.objects.filter(client=client).last().expressions.all()
        elif Client.objects.filter(employee=user):
            client = Client.objects.filter(employee=user).last()
            if ClientREFormats.objects.filter(client=client):
                expressions = ClientREFormats.objects.filter(client=client).last().expressions.all()
        return expressions
