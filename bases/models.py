# at w3chat/backend/bases/models.py
import uuid

# from django.core.validators import MinValueValidator
from django.db import models


class BaseModel(models.Model):
    """Define all common fields for all table."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )  # generate unique id.
    created_on = models.DateTimeField(
        auto_now_add=True
    )  # object creation time. will automatic generate
    updated_on = models.DateTimeField(
        auto_now=True
    )  # object update time. will automatic generate

    class Meta:
        abstract = True  # define this table/model is abstract.


class BaseModelWithOutId(models.Model):
    """Base Model with out id"""

    created_on = models.DateTimeField(
        auto_now_add=True
    )  # object creation time. will automatic generate
    updated_on = models.DateTimeField(
        auto_now=True
    )  # object update time. will automatic generate

    class Meta:
        abstract = True  # define this table/model is abstract.
