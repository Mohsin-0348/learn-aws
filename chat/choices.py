from django.db import models


class RegexChoice(models.TextChoices):
    PHONE_NUMBER = 'p'
    EMAIL = "e"
    URL = 'u'
