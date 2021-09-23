from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid

from .choices import RoleChoice, IdentifierBaseChoice
from .managers import UserManager, UserPasswordResetManager
from .tasks import send_email_on_delay
from bases.models import BaseModel


class User(AbstractUser, PermissionsMixin):
    """Store custom user information.
    all fields are common for all users."""
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=RoleChoice.choices, default=RoleChoice.CLIENT)  # role of user
    contact = models.CharField(max_length=16, blank=True, null=True)  # user phone number
    # Verification Check
    is_email_verified = models.BooleanField(
        default=False
    )  # if user verify his email address

    # permission
    is_superuser = models.BooleanField(
        default=False
    )  # main man of this application.
    is_deleted = models.BooleanField(
        default=False
    )  # if user account deleted by admins
    deleted_on = models.DateTimeField(
        null=True,
        blank=True
    )  # user account deletion time

    # details
    activation_token = models.UUIDField(
        blank=True,
        null=True
    )  # this token will be used for verify email-address
    deactivation_reason = models.TextField(
        null=True,
        blank=True
    )  # reason for deactivating user-account

    objects = UserManager()

    class Meta:
        db_table = f"{settings.DB_PREFIX}_users"
        # unique = ['email',]
        # ordering = ['-id']  # define default order as id in descending

    @property
    def is_admin(self):
        return self.is_superuser or self.is_staff

    def send_email_verification(self):
        self.activation_token = uuid.uuid4()
        self.is_email_verified = False
        self.save()
        print(self.activation_token)
        context = {
            'username': self.username,
            'email': self.email,
            'url': f"verify/{self.activation_token}/",
        }
        template = 'emails/sing_up_email.html'
        subject = 'Email Verification'
        send_email_on_delay.delay(template, context, subject, self.email)


class Client(BaseModel):
    auth_key = models.CharField(max_length=32)  # auto generate for uniquely define and will be used as encrypted
    admin = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="client_admin")  # define owner
    employee = models.ManyToManyField(User, blank=True, null=True,
                                      related_name='client_employees')  # define users who can check client information
    client_name = models.CharField(max_length=64, unique=True)  # store client who will use
    identifier_base = models.CharField(
        max_length=16, choices=IdentifierBaseChoice.choices,
        default=IdentifierBaseChoice.USER_TO_USER)  # base of chat system
    identifier_model_name = models.CharField(
        max_length=32, blank=True,
        null=True)  # if any identifier related to chat-module; will be used for redirection
    url = models.URLField(max_length=64)  # client website url

    class Meta:
        db_table = f"{settings.DB_PREFIX}_clients"
        ordering = ['-created_on']  # define default order as creation time in descending

    def __str__(self):
        return self.client_name


class UnitOfHistory(models.Model):
    action = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )  # in this field we will define which action was perform.
    created_on = models.DateTimeField(
        auto_now_add=True
    )  # object creation time. will automatic generate
    header = models.JSONField(
        null=True
    )  # request header that will provide user browser
    old_meta = models.JSONField(
        null=True
    )  # we store data what was the scenario before perform this action.
    new_meta = models.JSONField(
        null=True
    )  # we store data after perform this action.
    # Generic Foreignkey Configuration. DO NOT CHANGE
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.CharField(
        max_length=100
    )
    content_object = GenericForeignKey()

    class Meta:
        db_table = f"{settings.DB_PREFIX}_unit_of_histories"
        ordering = ['-created_on']  # define default order as creation time in descending

    @classmethod
    def user_history(
        cls,
        action,
        user,
        request,
        new_meta=None,
        old_meta=None,
        perform_for=None
    ) -> object:
        try:
            data = {i[0]: i[1] for i in request.META.items() if i[0].startswith('HTTP_')}
        except BaseException:
            data = None
        cls.objects.create(
            action=action,
            user=user,
            old_meta=old_meta,
            new_meta=new_meta,
            header=data,
            perform_for=perform_for,
            content_type=ContentType.objects.get_for_model(User),
            object_id=user.id
        )


class ResetPassword(models.Model):
    """
    Reset Password will store user data
    who request for reset password.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    token = models.UUIDField()
    updated_on = models.DateTimeField(
        auto_now=True
    )  # object update time. will automatic generate

    objects = UserPasswordResetManager()

    class Meta:
        db_table = f"{settings.DB_PREFIX}_users_password_reset"
        ordering = ['-updated_on']  # define default order as update time in descending

