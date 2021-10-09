import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

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
    photo = models.ImageField(upload_to='participant_photo', blank=True, null=True)
    is_online = models.BooleanField(default=False)
    count_connection = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = f"{settings.DB_PREFIX}_participants"  # define table name for database
        unique_together = (('client', 'user_id'),)  # unique user of client
        # ordering = ['-id']  # define default order as id in descending

    def __str__(self):
        return f"{self.name} : {self.is_online}"

    @property
    def unread_count(self):
        return len(ChatMessage.objects.filter(
            is_read=False, conversation__participants=self, is_deleted=False
        ).exclude(sender=self))


class Conversation(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING)  # client-info
    friendly_name = models.CharField(max_length=128, blank=True, null=True)
    identifier_id = models.CharField(max_length=128, blank=True, null=True)
    participants = models.ManyToManyField(Participant)
    connected = models.ManyToManyField(Participant, related_name="connected_users")
    is_blocked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_on']  # define default order as created in descending
        db_table = f"{settings.DB_PREFIX}_conversations"  # define table name for database

    def __str__(self):
        return str(self.id)

    @property
    def last_message(self):
        return self.messages.filter(is_deleted=False).first()

    def opposite_user(self, participant):
        return self.participants.exclude(id=participant.id).last()

    def unread_count(self, participant):
        return len(self.messages.filter(is_read=False, is_deleted=False).exclude(sender=participant))


class ChatMessage(models.Model):
    """
        Store message of users for a conversation.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages')  # define reference conversation for a message
    sender = models.ForeignKey(Participant, on_delete=models.DO_NOTHING,
                               related_name='sent_messages')  # define sender of the message
    message = models.TextField()  # define message body
    is_read = models.BooleanField(default=False)  # if receiver user read the message or not
    is_deleted = models.BooleanField(default=False)  # if sender want to remove the message
    deleted_from = models.ManyToManyField(Participant)
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
    updated_on = models.DateTimeField(
        auto_now=True
    )  # object update time. will automatic generate

    class Meta:
        db_table = f"{settings.DB_PREFIX}_chat_messages"  # define table name for database
        ordering = ['-created_on']  # define default order as created in descending
        get_latest_by = "created_on"  # define latest queryset by created

    @property
    def receiver(self):
        return self.conversation.participants.exclude(id=self.sender.id).last()


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
