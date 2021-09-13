from django.db import models


class RoleChoice(models.TextChoices):
    ADMIN = 'admin'
    MARKETING = 'marketing'
    SUPPORT = 'support'
    CLIENT = 'client'
    CLIENT_EMPLOYEE = 'client-employee'


class IdentifierBaseChoice(models.TextChoices):
    USER_TO_USER = 'user-to-user'
    IDENTIFIER_BASED = 'identifier-based'
