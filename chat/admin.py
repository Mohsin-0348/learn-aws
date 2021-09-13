from django.contrib import admin
from .models import Conversation, ChatMessage, Participant

admin.site.register(Conversation)
admin.site.register(ChatMessage)
admin.site.register(Participant)
