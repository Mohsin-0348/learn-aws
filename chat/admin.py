from django.contrib import admin

from chat.models import (
    ChatMessage,
    ClientOffensiveWords,
    ClientREFormats,
    Conversation,
    OffensiveWord,
    Participant,
    REFormat,
)

admin.site.register(Conversation)
admin.site.register(ChatMessage)
admin.site.register(Participant)
admin.site.register(OffensiveWord)
admin.site.register(REFormat)
admin.site.register(ClientOffensiveWords)
admin.site.register(ClientREFormats)
