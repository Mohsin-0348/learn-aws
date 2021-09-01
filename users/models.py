from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    photo = models.FileField(blank=True, null=True, upload_to='profile_photo')
