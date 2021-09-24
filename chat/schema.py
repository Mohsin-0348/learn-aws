# third party imports

import channels_graphql_ws
import django.contrib.auth
import graphene
from django.db.models import Q
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError

# local imports
from mysite.count_connection import CountConnection
from mysite.permissions import is_admin_user, is_authenticated, is_client_request
from users.models import UnitOfHistory
from users.choices import IdentifierBaseChoice

from chat.filters import ConversationFilters, MessageFilters, ParticipantFilters
from chat.models import Conversation, ChatMessage, Participant

User = django.contrib.auth.get_user_model()


class ConversationType(DjangoObjectType):
    """
        define django object type for chat model
    """
    object_id = graphene.ID()

    class Meta:
        model = Conversation
        filterset_class = ConversationFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class ParticipantType(DjangoObjectType):
    """
        define django object type for chat model
    """
    object_id = graphene.ID()

    class Meta:
        model = Participant
        filterset_class = ParticipantFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class ConversationQuery(graphene.ObjectType):
    """
        query all chat information
    """
    conversation = graphene.Field(ConversationType, id=graphene.ID())
    conversations = DjangoFilterConnectionField(ConversationType)
    user_conversation = graphene.Field(ConversationType, id=graphene.ID(), loaded_last=graphene.ID(required=False))
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
    def resolve_user_conversation(self, info, id, loaded_last=None, **kwargs):
        participant = info.context.participant
        conversation = Conversation.objects.get(id=id, participants=participant)
        messages = conversation.messages.all()
        if messages.filter(is_read=False) and messages.first().sender != participant:
            messages.filter(is_read=False).update(is_read=True)
        if loaded_last:
            loaded_last = ChatMessage.objects.get(id=loaded_last)
            messages = conversation.messages.all().filter(created_on__lt=loaded_last.created_on)
            messages = [obj for obj in messages]
            if len(messages) > 20:
                messages = messages[:20]
        else:
            messages = [obj for obj in conversation.messages.all()]
            if len(messages) > 20:
                messages = messages[:20]
        MessageSubscription.broadcast(payload=messages, group=str(conversation.id))
        return conversation

    @is_client_request
    def resolve_user_conversations(self, info, **kwargs):
        participant = info.context.participant
        objects = Conversation.objects.filter(participants=participant)
        object_list = [obj for obj in objects]
        ChatSubscription.broadcast(payload=object_list, group=str(participant.id))
        return objects


class StartConversation(graphene.Mutation):
    """
        create new chat information by a advertise
    """
    success = graphene.Boolean()
    message = graphene.String()
    conversation = graphene.Field(ConversationType)

    class Arguments:
        opposite_user = graphene.String(required=True)
        friendly_name = graphene.String(required=False)
        identifier_id = graphene.String(required=False)

    @is_client_request
    def mutate(self, info, opposite_user, friendly_name=None, identifier_id=None):
        participant = info.context.participant
        opposite_user, created = Participant.objects.get_or_create(client=participant.client, user_id=opposite_user)
        if not identifier_id and participant.client.identifier_base == IdentifierBaseChoice.IDENTIFIER_BASED:
            raise GraphQLError(
                message="Should include identifier-id",
                extensions={
                    "message": "Should include identifier-id",
                    "code": "invalid_request"
                }
            )
        if opposite_user and not Conversation.objects.filter(
                participants=participant).filter(participants=opposite_user):
            chat = Conversation.objects.create(
                client=participant.client, friendly_name=friendly_name,
                identifier_id=identifier_id
            )
            chat.participants.add(participant, opposite_user)
            objects = [obj for obj in Conversation.objects.filter(id=chat.id)]
            ChatSubscription.broadcast(payload=objects, group=str(participant.id))
            ChatSubscription.broadcast(payload=objects, group=str(opposite_user.id))
        elif Conversation.objects.filter(participants=participant).filter(participants=opposite_user):
            raise GraphQLError(
                message="Already have conversation.",
                extensions={
                    "message": "Already have conversation.",
                    "code": "invalid_request"
                }
            )
        else:
            raise GraphQLError(
                message="No participant added.",
                extensions={
                    "message": "No participant added.",
                    "code": "invalid_request"
                }
            )
        return StartConversation(
            success=True,
            conversation=chat,
            message="Successfully added"
        )


class MessageType(DjangoObjectType):
    """
        define django object type for message model
    """
    object_id = graphene.ID()

    class Meta:
        model = ChatMessage
        filterset_class = MessageFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class MessageQuery(graphene.ObjectType):
    """
        query all messages information for admin panel
    """
    all_messages = DjangoFilterConnectionField(MessageType)

    @is_admin_user
    def resolve_all_messages(self, info, **kwargs):
        return ChatMessage.objects.all()


class SendMessage(graphene.Mutation):
    """
        add new message by chat id, message and file
    """
    success = graphene.Boolean()
    message = graphene.Field(MessageType)

    class Arguments:
        chat_id = graphene.ID()
        message = graphene.String(required=False)
        file = Upload(required=False)

    @is_client_request
    def mutate(self, info, chat_id, message=None, file=None):
        client = info.context.client
        sender = info.context.participant
        chat = Conversation.objects.get(client=client, participants=sender, id=chat_id, is_blocked=False)
        if (not message or not message.strip()) and not file:
            raise GraphQLError(
                message="Invalid input request.",
                extensions={
                    "errors": {"message": "This field is required."},
                    "code": "invalid_input"
                }
            )
        elif file and (not message or not message.strip()):
            message = "Attachment"
        chat_message = ChatMessage.objects.create(conversation=chat, sender=sender, message=message, file=file)
        objects = [obj for obj in ChatMessage.objects.filter(id=chat_message.id)]
        MessageSubscription.broadcast(payload=objects, group=str(chat.id))
        return SendMessage(success=True, message=chat_message)


class BlockUserConversation(graphene.Mutation):
    """
        add new message by chat id, message and file
    """
    success = graphene.Boolean()
    message = graphene.String()
    conversation = graphene.Field(ConversationType)

    class Arguments:
        chat_id = graphene.ID()
        unblock = graphene.Boolean()

    @is_authenticated
    def mutate(self, info, chat_id, unblock=False, **kwargs):
        req_user = info.context.user
        chat = Conversation.objects.filter(client__admin=req_user, id=chat_id)
        if not chat:
            raise GraphQLError(
                message="Conversation not found.",
                extensions={
                    "errors": {"message": "Conversation not found."},
                    "code": "invalid_conversation"
                }
            )
        if unblock:
            chat.update(is_blocked=False)
        else:
            chat.update(is_blocked=True)
        return BlockUserConversation(
            success=True,
            message="Successfully unblocked" if unblock else "Successfully blocked",
            conversation=chat.first()
        )


class ChatSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    conversation = graphene.List(ConversationType)

    @staticmethod
    def subscribe(root, info):
        """Called when user subscribes."""
        if not info.context.user:
            raise GraphQLError(
                message="Invalid user!",
                extensions={
                    "message": "Invalid user!",
                    "code": "invalid_user"
                }
            )
        print("[subscribed to conversation]...", info.context.user)
        return [str(info.context.user.id)]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        print('[conversation published]...', info.context.user)
        return ChatSubscription(conversation=payload)


class MessageSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    messages = graphene.List(MessageType)
    conversation = graphene.Field(ConversationType)
    receiver = graphene.Field(ParticipantType)

    class Arguments:
        chat_id = graphene.ID()

    @staticmethod
    def subscribe(root, info, chat_id):
        """Called when user subscribes."""
        user = info.context.user
        if not user:
            raise GraphQLError(
                message="Invalid user!",
                extensions={
                    "message": "Invalid user!",
                    "code": "invalid_user"
                }
            )
        print('[subscribed to messaging]...', f"<{user}>")
        chat = Conversation.objects.filter(id=chat_id, participants=user)
        if not chat:
            raise GraphQLError(
                message="No conversation found!",
                extensions={
                    "message": "No conversation found!",
                    "code": "invalid_chat"
                }
            )

        return [chat_id]

    @staticmethod
    def publish(payload, info, chat_id):
        """Called to notify the client."""
        user = info.context.user
        print('[message published]...', f"<{user}>")
        chat = Conversation.objects.get(id=chat_id, participants=user)
        receiver = chat.participants.all().exclude(id=user.id).first()
        return MessageSubscription(messages=payload, conversation=chat, receiver=receiver)


class Query(ConversationQuery, MessageQuery, graphene.ObjectType):
    """
        define all the queries together
    """
    pass


class Mutation(graphene.ObjectType):
    """
        define all the mutations by identifier name for query
    """
    start_conversation = StartConversation.Field()
    send_message = SendMessage.Field()
    block_user_conversation = BlockUserConversation.Field()


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    chat_subscription = ChatSubscription.Field()
    message_subscription = MessageSubscription.Field()
