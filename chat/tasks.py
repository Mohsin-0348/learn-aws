from __future__ import absolute_import, unicode_literals

from django.utils import timezone

from chat.models import ChatMessage, Conversation, Participant
from chat.subscription import ChatSubscription, MessageSubscription
from mysite.celery import app


@app.task
def deliver_message(user_id):
    user = Participant.objects.get(id=user_id)
    messages = ChatMessage.objects.filter(
        conversation__participants=user, is_delivered=False, is_read=False, is_deleted=False
    ).exclude(sender=user)
    for msg in messages:
        msg.is_delivered = True
        msg.delivered_on = timezone.now()
        msg.save()
        if msg == msg.conversation.last_message and msg.sender.is_online:
            ChatSubscription.broadcast(payload=msg.conversation, group=str(msg.sender.id))
        if msg.sender in msg.conversation.connected.all():
            MessageSubscription.broadcast(payload=msg, group=str(msg.conversation.id))


@app.task
def send_status_to_others(user_id):
    user = Participant.objects.get(id=user_id)
    for chat in Conversation.objects.filter(participants=user):
        if chat.opposite_user(user).is_online:
            ChatSubscription.broadcast(payload=chat, group=str(chat.opposite_user(user).id))
