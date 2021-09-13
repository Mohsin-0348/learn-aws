
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from graphql import GraphQLError

from .models import UnitOfHistory

User = get_user_model()


def check_user(user, activate):
    if not user.is_admin and not user.is_email_verified:
        raise GraphQLError(
            message="Please verify email!",
            extensions={
                "message": "Please verify your email address.",
                "code": "unverified_email"
            }
        )
    elif not user.is_active and user.deactivation_reason:
        if activate:
            user.is_active = True
            user.deactivation_reason = None
            user.save()
        else:
            raise GraphQLError(
                message="Account is deactivated",
                extensions={
                    "message": "Account is deactivated",
                    "code": "account_not_active"
                }
            )
    elif not user.is_active:
        raise GraphQLError(
            message="Account is temporary blocked",
            extensions={
                "message": "Account is temporary blocked",
                "code": "account_blocked"
            }
        )
    return True


def signup(request, email, password, activate=False):
    try:
        user = User.objects.get(email=email)
        if check_user(user, activate):
            user = authenticate(
                username=user.username,
                password=password
            )
            if not user:
                raise GraphQLError(
                    message="Invalid credentials",
                    extensions={
                        "message": "invalid credentials",
                        "code": "invalid_credentials"
                    }
                )
            user.last_login = timezone.now()
            user.save()
            # UnitOfHistory.user_history(
            #     action=HistoryActions.USER_LOGIN,
            #     user=user,
            #     request=request
            # )
            return user
    except User.DoesNotExist:
        raise GraphQLError(
            message="Email is not associate with any existing user.",
            extensions={
                "message": "Email is not associate with any existing user.",
                "code": "invalid_email"
            }
        )
