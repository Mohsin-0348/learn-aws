import re

import django.contrib.auth
import graphene
from django.utils import timezone
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError

# local imports
from chat.choices import RegexChoice
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
from chat.query import (
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
from chat.tasks import deliver_message, send_status_to_others
from mysite.permissions import is_authenticated, is_client_request
from users.choices import IdentifierBaseChoice
from users.models import Client

# from users.models import UnitOfHistory

User = django.contrib.auth.get_user_model()


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
        if not chat.messages.all() or chat.last_message.created_on.date() != today:
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
        recipient_id = graphene.ID()

    @is_client_request
    def mutate(self, info, chat_id, recipient_id, **kwargs):
        # user = info.context.user
        # chat = Conversation.objects.get(participants=user, id=chat_id, is_blocked=False)
        TypingSubscription.broadcast(
            payload=str(chat_id), group=str(recipient_id)
        )
        return TypingMutation(success=True)


class UnsubscribeMutation(graphene.Mutation):
    success = graphene.Boolean()

    class Arguments:
        chat_id = graphene.ID()

    @is_client_request
    def mutate(self, info, chat_id, **kwargs):
        MessageSubscription.unsubscribe(group=str(chat_id))
        return TypingMutation(success=True)


class UserOnlineMutation(graphene.Mutation):
    success = graphene.Boolean()

    @is_client_request
    def mutate(self, info, **kwargs):
        user = info.context.user
        if not user.is_online:
            user.save()
            send_status_to_others.delay(user.id)
            deliver_message.delay(user.id)
        else:
            user.save()
        return UserOnlineMutation(success=True)


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
    unsubscribe = UnsubscribeMutation.Field()
    user_online = UserOnlineMutation.Field()
