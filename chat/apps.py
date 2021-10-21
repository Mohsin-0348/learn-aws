from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        try:
            from chat.models import ConnectedParticipantConversation
            ConnectedParticipantConversation.objects.all().delete()
        except Exception:
            pass
