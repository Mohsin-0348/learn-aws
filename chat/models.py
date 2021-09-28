import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from bases.models import BaseModel

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
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = f"{settings.DB_PREFIX}_participants"  # define table name for database
        unique_together = (('client', 'user_id'),)  # unique user of client
        # ordering = ['-id']  # define default order as id in descending

    def __str__(self):
        return f"{self.id}"


class Conversation(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING)  # client-info
    friendly_name = models.CharField(max_length=128, blank=True, null=True)
    identifier_id = models.CharField(max_length=128, blank=True, null=True)
    participants = models.ManyToManyField(Participant)
    is_blocked = models.BooleanField(default=False)
    # block_offense_word = models.BooleanField(default=False)
    # restrict_format = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_on']  # define default order as created in descending
        db_table = f"{settings.DB_PREFIX}_conversations"  # define table name for database

    def __str__(self):
        return str(self.id)


class ChatMessage(models.Model):
    """
        Store message of seller or buyer for a conversation.
        And help-query-user or admin user conversation message.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages')  # define reference conversation for a message
    sender = models.ForeignKey(Participant, on_delete=models.DO_NOTHING)  # define sender of the message
    message = models.TextField()  # define message body
    is_read = models.BooleanField(default=False)  # if receiver user read the message or not
    is_deleted = models.BooleanField(default=False)  # if sender want to remove the message
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


# class OffensiveWord(models.Model):
#     word = models.CharField(max_length=16)
#     user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="added_offensive_words")
#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)
#
#
# class ClientOffenseWord(models.Model):
#     client = models.OneToOneField(Client, on_delete=models.DO_NOTHING, related_name="offensive_word")  # client-info
#     words = models.ManyToManyField(OffensiveWord)
#
#
# class REFormat(models.Model):
#     expression = models.CharField(max_length=128)
#     user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="added_RE_formats")
#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)
#
#
# class ClientREFormats(models.Model):
#     client = models.OneToOneField(Client, on_delete=models.DO_NOTHING, related_name="RE_format")  # client-info
#     expressions = models.ManyToManyField(REFormat)
