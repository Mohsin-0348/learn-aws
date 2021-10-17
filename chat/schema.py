import re

import channels_graphql_ws
import django.contrib.auth
import graphene
from django.db.models import Q
from django.utils import timezone
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError

from chat.choices import RegexChoice

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
from mysite.permissions import is_admin_user, is_authenticated, is_client_request
from users.choices import IdentifierBaseChoice
from users.models import Client

# from users.models import UnitOfHistory

User = django.contrib.auth.get_user_model()


class ParticipantType(DjangoObjectType):
    """
        define django object type for chat model
    """
    object_id = graphene.ID()
    unread_count = graphene.Int()

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


class StartConversation(graphene.Mutation):
    """
        create new chat information by a advertise
    """
    success = graphene.Boolean()
    message = graphene.String()
    conversation = graphene.Field(ConversationType)

    class Arguments:
        opposite_user_id = graphene.String(required=True)
        opposite_username = graphene.String(required=True)
        friendly_name = graphene.String(required=False)
        identifier_id = graphene.String(required=False)
        user_photo = graphene.String(required=False)
        opposite_user_photo = graphene.String(required=False)

    @is_client_request
    def mutate(self, info, opposite_user_id, opposite_username, friendly_name=None, identifier_id=None,
               user_photo=None, opposite_user_photo=None):
        participant = info.context.user
        if participant and user_photo and participant.photo != user_photo:
            participant.photo = user_photo
            participant.save()
        opposite_user, created = Participant.objects.get_or_create(client=participant.client, user_id=opposite_user_id)
        if not identifier_id and participant.client.identifier_base == IdentifierBaseChoice.IDENTIFIER_BASED \
                and not friendly_name:
            raise GraphQLError(
                message="Should include identifier-id and friendly name",
                extensions={
                    "message": "Should include identifier-id and friendly name",
                    "code": "invalid_request"
                }
            )
        if not Conversation.objects.filter(
                participants=participant).filter(participants=opposite_user, identifier_id=identifier_id):
            if opposite_username != opposite_user.name:
                opposite_user.name = opposite_username
                opposite_user.save()
            if opposite_user.photo != opposite_user_photo:
                opposite_user.photo = opposite_user_photo
                opposite_user.save()
            chat = Conversation.objects.create(
                client=participant.client, friendly_name=friendly_name,
                identifier_id=identifier_id
            )
            chat.participants.add(participant, opposite_user)

            ChatSubscription.broadcast(payload=chat, group=str(participant.id))

            ChatSubscription.broadcast(payload=chat, group=str(opposite_user.id))
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


class UpdatePhoto(graphene.Mutation):
    """
        add new message by chat id, message and file
    """
    success = graphene.Boolean()
    participant = graphene.Field(ParticipantType)

    class Arguments:
        photo = graphene.String()

    @is_client_request
    def mutate(self, info, photo, **kwargs):
        participant = info.context.user
        if participant:
            participant.photo = photo
            participant.save()
        return UpdatePhoto(success=True, participant=participant)


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
        return ChatMessage.objects.all()

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
        return ChatMessage.objects.filter(conversation=conversation).exclude(deleted_from=participant)

    @is_client_request
    def resolve_user_favorite_messages(self, info, **kwargs):
        user = info.context.user
        user_fav, created = FavoriteMessage.objects.get_or_create(participant=user)
        return user_fav.messages.exclude(deleted_from=user)

    @is_client_request
    def resolve_message_count(self, info, **kwargs):
        return info.context.user.unread_count


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
        reply_to = graphene.ID(required=False)

    @is_client_request
    def mutate(self, info, chat_id, message=None, file=None, reply_to=None, **kwargs):
        client = info.context.client
        sender = info.context.user
        today = timezone.now().date()
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
        if client.block_offensive_word and ClientOffensiveWords.objects.filter(client=client):
            for word in ClientOffensiveWords.objects.get(client=client).words.all():
                if re.findall(str(word), message):
                    raise GraphQLError(
                        message=f"Using '{word}' is prohibited.",
                        extensions={
                            "errors": {"message": f"Using '{word}' is prohibited."},
                            "code": "invalid_input"
                        }
                    )
        if client.restrict_re_format and ClientREFormats.objects.filter(client=client):
            words = list(map(str, message.split()))
            for word in words:
                for expression in ClientREFormats.objects.get(client=client).expressions.all():
                    if (re.search(re.compile(expression.expression).pattern, word)):
                        raise GraphQLError(
                            message=f"'{word}' sharing is prohibited.",
                            extensions={
                                "errors": {"message": f"'{word}' sharing is prohibited."},
                                "code": "invalid_input"
                            }
                        )
        if reply_to:
            reply_to = ChatMessage.objects.get(id=reply_to, conversation=chat, is_deleted=False)
        if chat.last_message.created_on.date() != today:
            ChatMessage.objects.create(
                conversation=chat, sender=sender, message=str(today), message_type=ChatMessage.MessageType.DATE,
                is_read=True
            )
        chat_message = ChatMessage.objects.create(
            conversation=chat, sender=sender, message=message, file=file, reply_to=reply_to
        )
        if chat_message.receiver.is_online:
            chat_message.is_delivered = True
            chat_message.delivered_on = timezone.now()
            if chat_message.receiver in chat.connected.all():
                chat_message.is_read = True
                chat_message.read_on = timezone.now()
            else:
                MessageCountSubscription.broadcast(payload=chat_message.receiver.unread_count,
                                                   group=str(chat_message.receiver.id))
            chat_message.save()
            ChatSubscription.broadcast(payload=chat, group=str(chat_message.receiver.id))

        MessageSubscription.broadcast(payload=chat_message, group=str(chat.id))
        ChatSubscription.broadcast(payload=chat, group=str(sender.id))

        return SendMessage(success=True, message=chat_message)


class TypingMutation(graphene.Mutation):
    success = graphene.Boolean()

    class Arguments:
        chat_id = graphene.ID()

    @is_client_request
    def mutate(self, info, chat_id, **kwargs):
        user = info.context.user
        chat = Conversation.objects.get(participants=user, id=chat_id, is_blocked=False)
        TypingSubscription.broadcast(
            payload=str(chat.id), group=str(chat.opposite_user(user).id)
        )
        return TypingMutation(success=True)


class UnsubscribeMutation(graphene.Mutation):
    success = graphene.Boolean()

    class Arguments:
        chat_id = graphene.ID()

    @is_client_request
    def mutate(self, info, chat_id=None, **kwargs):
        user = info.context.user
        TypingSubscription.unsubscribe(group=str(user.id))
        return TypingMutation(success=True)


class DeleteId(graphene.InputObjectType):
    id = graphene.ID()


class DeleteMessages(graphene.Mutation):
    success = graphene.Boolean()

    class Arguments:
        message_ids = graphene.List(DeleteId)
        for_all = graphene.Boolean()

    @is_client_request
    def mutate(self, info, message_ids, for_all=False, **kwargs):
        participant = info.context.user
        message_ids = [id.id for id in message_ids]
        if message_ids and ChatMessage.objects.filter(id__in=message_ids, conversation__participants=participant,
                                                      is_deleted=False).exclude(deleted_from=participant):
            messages = ChatMessage.objects.filter(id__in=message_ids, conversation__participants=participant,
                                                  is_deleted=False).exclude(deleted_from=participant)
            if for_all:
                all_messages = messages.filter(is_read=False)
                conversation = messages.last().conversation
                if len(messages) != len(all_messages):
                    raise GraphQLError(
                        message="Invalid request.",
                        extensions={
                            "errors": {"messageIds": "User can't delete read messages."},
                            "code": "invalid_request"
                        }
                    )
                all_messages = all_messages.filter(sender=participant)
                if len(messages) != len(all_messages):
                    raise GraphQLError(
                        message="Invalid request.",
                        extensions={
                            "errors": {"messageIds": "User can't delete other sender's messages."},
                            "code": "invalid_request"
                        }
                    )

                for msg in all_messages:
                    msg.is_deleted = True
                    msg.save()
                    MessageSubscription.broadcast(payload=msg, group=str(msg.conversation.id))
                    if msg == conversation.last_message:
                        ChatSubscription.broadcast(
                            payload=conversation, group=str(msg.receiver.id)
                        )
                        ChatSubscription.broadcast(
                            payload=conversation, group=str(msg.sender.id)
                        )
            else:
                for msg in messages:
                    msg.deleted_from.add(participant)
                    MessageSubscription.broadcast(payload=msg, group=str(msg.conversation.id))
                    if msg == msg.conversation.last_message:
                        ChatSubscription.broadcast(
                            payload=msg.conversation, group=str(participant.id)
                        )
        else:
            raise GraphQLError(
                message="Invalid input request.",
                extensions={
                    "errors": {"messageIds": "No message found for deleting."},
                    "code": "invalid_input"
                }
            )
        return DeleteMessages(success=True)


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


class FavoriteMessageMutation(graphene.Mutation):
    success = graphene.Boolean()
    object = graphene.Field(MessageType)
    message = graphene.String()

    class Arguments:
        message_id = graphene.ID()
        add = graphene.Boolean()

    @is_client_request
    def mutate(self, info, message_id, add=True, **kwargs):
        user = info.context.user
        message_obj = ChatMessage.objects.get(id=message_id, conversation__participants=user)
        user_favorite, created = FavoriteMessage.objects.get_or_create(participant=user)
        if add:
            user_favorite.messages.add(message_obj)
        elif not add and user_favorite.messages.filter(id=message_id):
            user_favorite.messages.remove(message_obj)
        else:
            raise GraphQLError(
                message="Message not added yet to favorite.",
                extensions={
                    "errors": {"message": "Message not added yet to favorites."},
                    "code": "invalid_action"
                }
            )
        return FavoriteMessageMutation(
            success=True, object=message_obj, message="Successfully added" if add else "Successfully removed"
        )


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


class OffensiveWordMutation(graphene.Mutation):
    success = graphene.String()
    message = graphene.String()
    object = graphene.Field(OffensiveWordType)

    class Arguments:
        word = graphene.String()
        remove = graphene.Boolean()

    @is_authenticated
    def mutate(self, info, word, remove=False, **kwargs):
        user = info.context.user
        if not word.strip():
            raise GraphQLError(
                message="Invalid input.",
                extensions={
                    "errors": {"word": "This field is required."},
                    "code": "invalid_input"
                }
            )
        message = "Successfully added"
        if not user.is_admin:
            client = Client.objects.get(admin=user)
            if remove:
                word_client, added = ClientOffensiveWords.objects.get_or_create(client=client)
                object = OffensiveWord.objects.get(word=word)
                word_client.words.get(word=object.word)
                word_client.words.remove(object)
                message = "Successfully removed"
            else:
                object, created = OffensiveWord.objects.get_or_create(word=word)
                word_client, added = ClientOffensiveWords.objects.get_or_create(client=client)
                word_client.words.add(object)
        else:
            object = OffensiveWord.objects.create(word=word)
        return OffensiveWordMutation(
            success=True,
            message=message,
            object=object
        )


class REFormatMutation(graphene.Mutation):
    success = graphene.String()
    message = graphene.String()
    object = graphene.Field(REFormatType)

    class Arguments:
        expression = graphene.String()
        remove = graphene.Boolean()

    @is_authenticated
    def mutate(self, info, expression, remove=False, **kwargs):
        user = info.context.user
        if not expression.strip() or expression not in RegexChoice.choices:
            raise GraphQLError(
                message="Invalid input.",
                extensions={
                    "errors": {"expression": "This field is required."},
                    "code": "invalid_input"
                }
            )
        message = "Successfully added"
        if not user.is_admin:
            client = Client.objects.get(admin=user)
            if remove:
                expression_client, added = ClientREFormats.objects.get_or_create(client=client)
                object = REFormat.objects.get(expression=expression)
                expression_client.words.get(expression=object.expression)
                expression_client.expressions.remove(object)
                message = "Successfully removed"
            else:
                object, created = REFormat.objects.get_or_create(expression=expression)
                expression_client, added = ClientREFormats.objects.get_or_create(client=client)
                expression_client.expressions.add(object)
        else:
            object = REFormat.objects.create(expression=expression)
        return REFormatMutation(success=True, object=object, message=message)


class ChatSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    conversation = graphene.Field(ConversationType)

    @staticmethod
    def subscribe(root, info):
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
        info.context.chat_connection = True
        user.count_connection += 1
        user.is_online = True
        user.save()
        print(f"[subscribed to conversation]... <{user}>")
        return [str(user.id)]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        print(f"[conversation published]... <{info.context.user}>")
        return ChatSubscription(conversation=payload)


class MessageSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    message = graphene.Field(MessageType)
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
        chat = Conversation.objects.filter(id=chat_id, participants=user)
        if not chat:
            raise GraphQLError(
                message="No conversation found!",
                extensions={
                    "message": "No conversation found!",
                    "code": "invalid_chat"
                }
            )
        chat.last().connected.add(user)
        info.context.chats = str(chat.last().id)
        print(f"[subscribed to messaging]... <{user}> | {chat.last().id}")
        return [chat_id]

    @staticmethod
    def publish(payload, info, chat_id):
        """Called to notify the client."""
        user = info.context.user
        chat = Conversation.objects.get(id=chat_id, participants=user)
        receiver = chat.participants.all().exclude(id=user.id).first()
        print(f"[message published]... <{user}> | {chat.id}")
        return MessageSubscription(message=payload, receiver=receiver)


class MessageCountSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    count = graphene.Int()

    @staticmethod
    def subscribe(root, info):
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
        info.context.chat_connection = True
        user.count_connection += 1
        user.is_online = True
        user.save()
        print(f"[subscribed to count]... <{user}>")
        return [str(info.context.user.id)]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        print(f"[count published]... <{info.context.user}>")
        return MessageCountSubscription(count=payload)


class TypingSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    chat_id = graphene.String()

    @staticmethod
    def subscribe(root, info):
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
        print(f"[subscribed to typing]... <{user}>")
        return [str(user.id)]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        user = info.context.user
        print(f"[typing published]... <{user}>")
        return TypingSubscription(chat_id=payload)


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


class Mutation(graphene.ObjectType):
    """
        define all the mutations by identifier name for query
    """
    start_conversation = StartConversation.Field()
    update_photo = UpdatePhoto.Field()
    send_message = SendMessage.Field()
    block_user_conversation = BlockUserConversation.Field()
    add_or_remove_offensive_word = OffensiveWordMutation.Field()
    add_or_remove_expression = REFormatMutation.Field()
    delete_messages = DeleteMessages.Field()
    typing_mutation = TypingMutation.Field()
    favorite_message_mutation = FavoriteMessageMutation.Field()
    # unsubscribe = UnsubscribeMutation.Field()


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    chat_subscription = ChatSubscription.Field()
    message_subscription = MessageSubscription.Field()
    message_count_subscription = MessageCountSubscription.Field()
    typing_subscription = TypingSubscription.Field()
