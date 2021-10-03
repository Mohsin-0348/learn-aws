from django.db import models


class RegexChoice(models.TextChoices):
    PHONE_NUMBER = r"^\+?1?\d{9,15}$"
    EMAIL = r"^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
    URL = r"u"
