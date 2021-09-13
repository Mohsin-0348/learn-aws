
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from .choices import RoleChoice


class UserManager(BaseUserManager):
    def create_base(
        self,
        username,
        email,
        password,
        is_staff,
        is_superuser,
        **extra_fields
    ) -> object:
        """
        Create User With Email name password
        """
        if not email:
            raise ValueError("User must have an email")
        if not username:
            raise ValueError("User must have an username")
        user = self.model(
            username=username,
            email=email,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_user(
        self,
        username,
        email,
        password=None,
        **extra_fields
    ) -> object:
        """Creates and save non-staff-normal user
        with given username, email, username and password."""

        return self.create_base(
            username,
            email,
            password,
            False,
            False,
            **extra_fields
        )

    def create_superuser(
        self,
        username,
        email,
        password,
        **extra_fields
    ) -> object:
        """Creates and saves super user
        with given username, email, name and password."""
        return self.create_base(
            username,
            email,
            password,
            True,
            True,
            role=RoleChoice.ADMIN,
            **extra_fields
        )


class UserPasswordResetManager(BaseUserManager):

    def check_key(self, token, email):
        if not token:
            return False

        try:
            row = self.get(token=token, user__email=email)
            if row.updated_on + timezone.timedelta(minutes=5) > timezone.now():
                return False
            row.delete()
            return True
        except self.model.DoesNotExist:
            return False

    def create_or_update(self, user, token):
        try:
            row = self.get(user=user)
            row.token = token
            row.save()
            return row
        except self.model.DoesNotExist:
            return self.create(user=user, token=token)
