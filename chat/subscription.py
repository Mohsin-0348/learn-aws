import channels_graphql_ws
import django.contrib.auth
import graphene
from graphql import GraphQLError

# local imports
from chat.models import Conversation
from chat.object_types import ConversationType, MessageType, ParticipantType

User = django.contrib.auth.get_user_model()


class UserSubscription(channels_graphql_ws.Subscription):
    """
        Pass user info whenever any user come online.
        This will take no parameter for subscribing.
        And will broadcast participant object.
    """

    # Subscription payload.
    user = graphene.Field(ParticipantType)

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
        print(f"[subscribed to channel]... <{user}>")
        return ["users-channel"]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        print(f"[user payload received]... <{info.context.user}>")
        return UserSubscription(user=payload)


class ChatSubscription(channels_graphql_ws.Subscription):
    """
        Pass conversation info to users.
        This will take no parameter for subscribing.
        And will broadcast conversation object.
    """

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
        print(f"[conversation payload received]... <{info.context.user}>")
        return ChatSubscription(conversation=payload)


class MessageSubscription(channels_graphql_ws.Subscription):
    """
        Pass message info to the users of a conversation.
        This will take the conversation id as parameter for subscribing.
        And will broadcast message object.
    """

    # Subscription payload.
    message = graphene.Field(MessageType)

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
        chat = Conversation.objects.filter(id=chat_id, participants=user).last()
        if not chat:
            raise GraphQLError(
                message="No conversation found!",
                extensions={
                    "message": "No conversation found!",
                    "code": "invalid_chat"
                }
            )
        chat.connected.through.objects.create(conversation=chat, participant=user,
                                              connection_token=info.context.connection_token)
        print(f"[subscribed to messaging]... <{user}> | {chat.id}")
        return [chat_id]

    @staticmethod
    def publish(payload, info, chat_id):
        """Called to notify the client."""
        user = info.context.user
        print(f"[message payload received]... <{user}> | {chat_id}")
        return MessageSubscription(message=payload)

    @staticmethod
    def unsubscribed(root, info, chat_id, *args, **kwds):
        user = info.context.user
        chat = Conversation.objects.get(id=chat_id, participants=user)
        chat.connected.through.objects.filter(conversation=chat, participant=user,
                                              connection_token=info.context.connection_token).delete()
        print(f"[unsubscribed from messaging]... <{user}> | {chat_id}")


class MessageCountSubscription(channels_graphql_ws.Subscription):
    """
        Pass unread message count to user.
        This will take no parameter for subscribing.
        And will return count of unread messages.
    """

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
        print(f"[subscribed to count]... <{user}>")
        return [str(info.context.user.id)]

    @staticmethod
    def publish(payload, info):
        """Called to notify the client."""
        print(f"[count payload received]... <{info.context.user}>")
        return MessageCountSubscription(count=payload)


class TypingSubscription(channels_graphql_ws.Subscription):
    """
        Pass typing response whenever any user types for messaging.
        This will take no parameter for subscribing.
        And will return true as typing response.
    """

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
        print(f"[typing payload received]... <{user}>")
        return TypingSubscription(chat_id=payload)


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    user_subscription = UserSubscription.Field()
    chat_subscription = ChatSubscription.Field()
    message_subscription = MessageSubscription.Field()
    message_count_subscription = MessageCountSubscription.Field()
    typing_subscription = TypingSubscription.Field()
