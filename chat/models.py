import datetime
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from bases.models import BaseModel
from chat.choices import RegexChoice

# define local imports
from users.models import Client

User = get_user_model()  # define user model


class Participant(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )  # generate unique participant-id.
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING)  # client-info
    name = models.CharField(max_length=128)  # will provided from client-app
    user_id = models.CharField(max_length=128)  # will provided from client-app
    photo = models.TextField(blank=True, null=True)
    last_seen = models.DateTimeField(auto_now=True)
    # is_online = models.BooleanField(default=False)
    # count_connection = models.PositiveIntegerField(default=0)

    @property
    def is_online(self):
        return timezone.now() < self.last_seen + datetime.timedelta(minutes=settings.OFFLINE_TIME_DELTA_MINUTES)

    @property
    def unread_count(self):
        return len(ChatMessage.objects.filter(
            read_on__isnull=True, conversation__participants=self, is_deleted=False
        ).exclude(sender=self))

    def __str__(self):
        return f"{self.name} : {self.is_online}"

    class Meta:
        db_table = f"{settings.DB_PREFIX}_participants"  # define table name for database
        unique_together = (('client', 'user_id'),)  # unique user of client


class ConnectedParticipantConversation(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='connected_conversation')
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE,
                                     related_name='connected_participants')
    # connection_count = models.PositiveIntegerField(default=1)
    connection_token = models.UUIDField()


class Conversation(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING)  # client-info
    friendly_name = models.CharField(max_length=128, blank=True, null=True)
    identifier_id = models.CharField(max_length=128, blank=True, null=True)
    participants = models.ManyToManyField(Participant)
    connected = models.ManyToManyField(Participant, related_name="connected_users",
                                       through=ConnectedParticipantConversation)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

    @property
    def last_message(self):
        return self.messages.first()

    def opposite_user(self, participant):
        return self.participants.exclude(id=participant.id).last()

    def unread_count(self, participant):
        return len(self.messages.filter(read_on__isnull=True, is_deleted=False).exclude(sender=participant))

    class Meta:
        ordering = ['-created_on']  # define default order as created in descending
        db_table = f"{settings.DB_PREFIX}_conversations"  # define table name for database


class ChatMessage(models.Model):
    """
        Store message of users for a conversation.
    """
    class MessageType(models.TextChoices):
        MESSAGE = 'message'
        DATE = 'date'
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.MESSAGE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages')  # define reference conversation for a message
    sender = models.ForeignKey(Participant, on_delete=models.DO_NOTHING,
                               related_name='sent_messages')  # define sender of the message
    message = models.TextField()  # define message body
    read_on = models.DateTimeField(blank=True, null=True)  # time of message seen
    delivered_on = models.DateTimeField(blank=True, null=True)  # time of message delivery
    is_deleted = models.BooleanField(default=False)  # if sender want to remove the message
    deleted_from = models.ManyToManyField(Participant)
    reply_to = models.ForeignKey('self', on_delete=models.DO_NOTHING, related_name="reply_for", null=True)
    file = models.FileField(
        upload_to="conversation/",
        blank=True,
        null=True,
        verbose_name="Shared File",
        help_text="File shared in a conversation"
    )  # store a file information if uploaded
    created_on = models.DateTimeField(
        auto_now_add=True
    )  # object creation time. will automatic generate

    class Meta:
        db_table = f"{settings.DB_PREFIX}_chat_messages"  # define table name for database
        verbose_name = "Message"
        ordering = ['-created_on']  # define default order as created in descending
        get_latest_by = "created_on"  # define latest queryset by created

    @property
    def receiver(self):
        return self.conversation.participants.exclude(id=self.sender.id).last()

    def is_favorite(self, user):
        user_fav, created = FavoriteMessage.objects.get_or_create(participant=user)
        if user_fav.messages.filter(id=self.id):
            return True
        return False

    @property
    def status(self):
        if self.read_on:
            return "seen"
        elif not self.read_on and self.delivered_on:
            return "delivered"
        return "sent"


class FavoriteMessage(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.DO_NOTHING,
                                    related_name='favorite_messages')  # define user who added favorite
    messages = models.ManyToManyField(ChatMessage)

    class Meta:
        db_table = f"{settings.DB_PREFIX}_favorite_messages"  # define table name for database


class OffensiveWord(models.Model):
    word = models.CharField(max_length=16, unique=True)

    def __str__(self):
        return self.word


class ClientOffensiveWords(models.Model):
    client = models.OneToOneField(Client, on_delete=models.DO_NOTHING, related_name="offensive_word")  # client-info
    words = models.ManyToManyField(OffensiveWord)

    class Meta:
        verbose_name_plural = "ClientOffensiveWords"


class REFormat(models.Model):
    expression = models.CharField(max_length=128, unique=True, choices=RegexChoice.choices)

    def __str__(self):
        return self.expression


class ClientREFormats(models.Model):
    client = models.OneToOneField(Client, on_delete=models.DO_NOTHING, related_name="RE_format")  # client-info
    expressions = models.ManyToManyField(REFormat)

    class Meta:
        verbose_name_plural = "ClientREFormats"
