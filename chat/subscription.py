
import channels_graphql_ws
import django.contrib.auth
import graphene
from graphql import GraphQLError

# local imports
from chat.models import Conversation
from chat.object_types import ConversationType, MessageType, ParticipantType

User = django.contrib.auth.get_user_model()


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
        # user.save()
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
        # user.save()
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

    @staticmethod
    def unsubscribed(root, info, chat_id, *args, **kwds):
        user = info.context.user
        chat = Conversation.objects.get(id=chat_id, participants=user)
        chat.connected.remove(user)
        print("from unsubscribed", info.context)


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
        # user.save()
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


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    chat_subscription = ChatSubscription.Field()
    message_subscription = MessageSubscription.Field()
    message_count_subscription = MessageCountSubscription.Field()
    typing_subscription = TypingSubscription.Field()
