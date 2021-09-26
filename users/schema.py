from django.utils import timezone
from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.forms.mutation import DjangoFormMutation
from graphql import GraphQLError

import graphene

from users.choices import RoleChoice, IdentifierBaseChoice
from users.filters import UserFilters, LogsFilters, ClientFilters
from users.forms import UserRegistrationForm, ClientForm, ClientEmployeeForm
from users.login_backend import signup
from users.models import ResetPassword, Client, UnitOfHistory
from users.tasks import send_password_reset_mail
from mysite.permissions import is_authenticated, is_admin_user
from mysite.authentication import TokenManager
from mysite.count_connection import CountConnection
from bases.utils import generate_auth_key, create_token
from bases.constants import HistoryActions

User = get_user_model()


class UserType(DjangoObjectType):
    object_id = graphene.ID()

    class Meta:
        model = User
        filterset_class = UserFilters
        interfaces = (graphene.relay.Node,)
        convert_choices_to_enum = False
        connection_class = CountConnection

    @staticmethod
    def resolve_object_id(self, info, **kwargs):
        return self.pk


class LogType(DjangoObjectType):
    class Meta:
        model = UnitOfHistory
        filterset_class = LogsFilters
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection


class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        filterset_class = ClientFilters
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection


class LoginUser(graphene.Mutation):
    success = graphene.Boolean()
    access = graphene.String()
    refresh = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        activate = graphene.Boolean()

    def mutate(self, info, email, password, activate=False):
        user = signup(info.context, email, password, activate)
        access = TokenManager.get_access({"user_id": str(user.id)})
        refresh = TokenManager.get_refresh({"user_id": str(user.id)})
        # UnitOfHistory.user_history(
        #     action=HistoryActions.USER_LOGIN,
        #     user=user,
        #     request=info.context,
        # )
        return LoginUser(
            access=access,
            refresh=refresh,
            user=user,
            success=True
        )


class RegisterUser(DjangoFormMutation):
    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Meta:
        form_class = UserRegistrationForm

    def mutate_and_get_payload(self, info, **input):
        form = UserRegistrationForm(data=input)
        if form.is_valid():
            if form.cleaned_data['password'] and validate_password(form.cleaned_data['password']):
                pass
            user = User.objects.create_user(**form.cleaned_data)
            user.send_email_verification()
        else:
            error_data = {}
            for error in form.errors:
                for err in form.errors[error]:
                    error_data[error] = err
            raise GraphQLError(
                message="Invalid input request.",
                extensions={
                    "errors": error_data,
                    "code": "invalid_input"
                }
            )
        # UnitOfHistory.user_history(
        #     action=HistoryActions.USER_SIGNUP,
        #     user=user,
        #     request=info.context,
        #     new_meta=model_to_dict(user)
        # )
        return RegisterUser(
            message="A mail was sent to this email address.",
            user=user,
            success=True
        )


class VerifyEmail(graphene.Mutation):
    """
    Verify Mutation::
    will define your access token expired or not.
    """

    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        token = graphene.String(required=True)

    def mutate(self, info, token):
        user_exist = User.objects.filter(activation_token=token)
        if user_exist:
            if user_exist.filter(is_email_verified=True):
                raise GraphQLError(
                    message="User already verified.",
                    extensions={
                        "errors": "User already verified.",
                        "code": "already_verified"
                    }
                )
            user = user_exist.last()
            user_exist.update(is_email_verified=True, activation_token=None)
        else:
            raise GraphQLError(
                message="Invalid token!",
                extensions={
                    "errors": "Invalid token!",
                    "code": "invalid_token"
                }
            )
        # UnitOfHistory.user_history(
        #     action=HistoryActions.EMAIL_VERIFIED,
        #     user=user,
        #     request=info.context,
        # )
        return VerifyEmail(
            success=True,
            user=user,
            message="User activation was successful."
        )


class ResendActivationMail(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        email = graphene.String(required=True)

    def mutate(self, info, email):
        user_exist = User.objects.filter(email=email)
        if user_exist:
            if user_exist.filter(is_email_verified=True):
                raise GraphQLError(
                    message="User already verified.",
                    extensions={
                        "errors": "User already verified.",
                        "code": "already_verified"
                    }
                )
            user_exist.last().send_email_verification()
        else:
            raise GraphQLError(
                message="Invalid email!",
                extensions={
                    "errors": "Invalid email address!",
                    "code": "invalid_email"
                }
            )
        # UnitOfHistory.user_history(
        #     action=HistoryActions.RESEND_ACTIVATION,
        #     user=user_exist.last(),
        #     request=info.context,
        # )
        return ResendActivationMail(
            success=True,
            user=user_exist.last(),
            message="Mail sent successfully."
        )


class PasswordChange(graphene.Mutation):
    """
    Password Change Mutation::
    Password change by using old password.
    password length should min 8.
    not similar to username or email.
    password must contain number
    """

    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        old_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    @is_authenticated
    def mutate(self, info, old_password, new_password):
        user = info.context.user
        if not user.check_password(old_password):
            raise GraphQLError(
                message="password does not match.",
                extensions={
                    "message": "password does not match.",
                    "code": "invalid_password"
                }
            )

        validate_password(new_password)
        user.set_password(new_password)
        user.save()
        # UnitOfHistory.user_history(
        #     action=HistoryActions.PASSWORD_CHANGE,
        #     user=user,
        #     request=info.context
        # )
        return PasswordChange(
            success=True,
            message="Password change successful",
            user=user
        )


class PasswordResetMail(graphene.Mutation):
    """
        Password Rest Mail mutation::
        User will be able to Request Rest their password.
        by using register email.
    """

    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        email = graphene.String(required=True)

    def mutate(self, info, email):
        user = User.objects.filter(email=email).first()
        if not user:
            raise Exception("no user associate with this email")
        token = create_token()
        ResetPassword.objects.create_or_update(user, token)
        print(token)
        send_password_reset_mail.delay(email, token)
        # UnitOfHistory.user_history(
        #     action=HistoryActions.PASSWORD_RESET_REQUEST,
        #     user=user,
        #     request=info.context
        # )
        return PasswordResetMail(
            success=True,
            message="Password reset mail send successfully"
        )


class PasswordResetMutation(graphene.Mutation):
    """
    Password Rest Mutation::
    after getting rest mail user will
    get a link to reset password.
    To verify Password:
        1. password length should min 8.
        2. not similar to username or email.
        3. password must contain number
    """

    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        email = graphene.String(required=True)
        token = graphene.String(required=True)
        password1 = graphene.String(required=True)
        password2 = graphene.String(required=True)

    def mutate(
            self,
            info,
            email,
            token,
            password1,
            password2
    ):
        user = User.objects.filter(email=email).first()
        if not user:
            raise Exception("no user associate with this email")
        if not ResetPassword.objects.check_key(token, email):
            raise Exception("Token expired!")
        validate_password(password1)
        if not password1 == password2:
            raise Exception("Password not match")
        user.set_password(password2)
        user.save()
        # UnitOfHistory.user_history(
        #     action=HistoryActions.PASSWORD_RESET,
        #     user=user,
        #     request=info.context
        # )
        return PasswordResetMutation(
            success=True,
            message="Password reset successful",
        )


class ClientMutation(DjangoFormMutation):
    success = graphene.Boolean()
    message = graphene.String()
    client = graphene.Field(ClientType)

    class Meta:
        form_class = ClientForm

    @is_authenticated
    def mutate_and_get_payload(self, info, **input):
        user = info.context.user
        if user.role != RoleChoice.CLIENT:
            raise GraphQLError(
                message="Role of user not client.",
                extensions={
                    "errors": "Role of user not client.",
                    "code": "invalid_request"
                }
            )
        form = ClientForm(data=input)
        if form.is_valid():
            client_exist = Client.objects.filter(admin=user)
            if form.cleaned_data['identifier_base'] == IdentifierBaseChoice.IDENTIFIER_BASED and not form.cleaned_data[
                'identifier_model_name']:
                raise GraphQLError(
                    message="Should include identifier route.",
                    extensions={
                        "errors": "Should include identifier route.",
                        "code": "invalid_request"
                    }
                )
            if client_exist:
                client = client_exist.last()
                client_exist.update(**form.cleaned_data)
            else:
                form.cleaned_data = form.cleaned_data.copy()
                form.cleaned_data['admin'] = user
                form.cleaned_data['auth_key'] = generate_auth_key()
                client = Client.objects.create(**form.cleaned_data)
        else:
            error_data = {}
            for error in form.errors:
                for err in form.errors[error]:
                    error_data[error] = err
            raise GraphQLError(
                message="Invalid input request.",
                extensions={
                    "errors": error_data,
                    "code": "invalid_input"
                }
            )
        # UnitOfHistory.user_history(
        #     action=HistoryActions.CLIENT_INFO_UPDATED,
        #     user=client.user,
        #     request=info.context,
        # )
        return ClientMutation(
            message="successfully registered.",
            client=client,
            success=True
        )


class RegisterClientEmployee(DjangoFormMutation):
    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Meta:
        form_class = UserRegistrationForm

    @is_authenticated
    def mutate_and_get_payload(self, info, **input):
        user = info.context.user
        if not user.client_admin.all():
            raise GraphQLError(
                message="User didn't add any client information.",
                extensions={
                    "errors": "User didn't add any client information.",
                    "code": "invalid_request"
                }
            )
        form = UserRegistrationForm(data=input)
        if form.is_valid():
            form.cleaned_data = form.cleaned_data.copy()
            form.cleaned_data['role'] = RoleChoice.CLIENT_EMPLOYEE
            if form.cleaned_data['password'] and validate_password(form.cleaned_data['password']):
                pass
            employee = User.objects.create_user(**form.cleaned_data)
            user.client_admin.first().employee.add(employee)
            employee.send_email_verification()
        else:
            error_data = {}
            for error in form.errors:
                for err in form.errors[error]:
                    error_data[error] = err
            raise GraphQLError(
                message="Invalid input request.",
                extensions={
                    "errors": error_data,
                    "code": "invalid_input"
                }
            )
        # UnitOfHistory.user_history(
        #     action=HistoryActions.CLIENT_EMPLOYEE_ADDED,
        #     user=user,
        #     request=info.context,
        # )
        return RegisterClientEmployee(
            message="A mail was sent to this email address.",
            user=employee,
            success=True
        )


class DeleteClientEmployee(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        email = graphene.String()

    @is_authenticated
    def mutate(self, info, email, **kwargs):
        user = info.context.user
        if not user.client_admin.all():
            raise GraphQLError(
                message="User didn't add any client information.",
                extensions={
                    "errors": "User didn't add any client information.",
                    "code": "invalid_request"
                }
            )
        elif not user.client_admin.first().employee.filter(email=email):
            raise GraphQLError(
                message="Client employee email is not valid.",
                extensions={
                    "errors": "Client employee email is not valid.",
                    "code": "invalid_email"
                }
            )
        else:
            employee = User.objects.get(email=email)
            user.client_admin.first().employee.remove(employee)
            employee.is_active = False
            employee.deactivation_reason = None
            employee.is_deleted = True
            employee.deleted_on = timezone.now()
            employee.save()
        # UnitOfHistory.user_history(
        #     action=HistoryActions.CLIENT_EMPLOYEE_REMOVED,
        #     user=user,
        #     request=info.context,
        # )
        return DeleteClientEmployee(
            message="Client employee was removed",
            user=employee,
            success=True
        )


class Query(graphene.ObjectType):
    users = DjangoFilterConnectionField(UserType)
    user = graphene.relay.Node.Field(UserType)
    logs = DjangoFilterConnectionField(LogType)
    log = graphene.relay.Node.Field(LogType)
    me = graphene.Field(UserType)

    @is_authenticated
    def resolve_me(self, info, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError(
                message='Your are not login',
                extensions={
                    "message": "Your are not login",
                    "code": "unauthorised"
                })
        return user

    @is_admin_user
    def resolve_users(self, info, **kwargs):
        return User.objects.all()

    @is_admin_user
    def resolve_logs(self, info, **kwargs):
        return UnitOfHistory.objects.all()


class Mutation(graphene.ObjectType):
    login_user = LoginUser.Field()
    register_user = RegisterUser.Field()
    verify_email = VerifyEmail.Field()
    resend_activation_mail = ResendActivationMail.Field()
    password_change = PasswordChange.Field()
    password_reset = PasswordResetMutation.Field()
    password_reset_mail = PasswordResetMail.Field()

    update_client_info = ClientMutation.Field()
    add_client_employee = RegisterClientEmployee.Field()
    delete_client_employee = DeleteClientEmployee.Field()

