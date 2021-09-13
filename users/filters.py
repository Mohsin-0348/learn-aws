from django.contrib.auth import get_user_model
import django_filters as filters

from bases.filters import BaseFilters
from .models import UnitOfHistory, Client

User = get_user_model()


class UserFilters(BaseFilters):
    username = filters.CharFilter(field_name="username", lookup_expr="icontains")
    email = filters.CharFilter(field_name="username", lookup_expr="icontains")

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            'first_name',
            'last_name',
            'is_email_verified',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_deleted',
        ]


class LogsFilters(BaseFilters):
    action = filters.CharFilter(
        field_name='action',
        lookup_expr='icontains'
    )

    class Meta:
        model = UnitOfHistory
        fields = [
            'id',
            'action',
            'created_on',
        ]


class ClientFilters(BaseFilters):
    client_name = filters.CharFilter(
        field_name='client_name',
        lookup_expr='icontains'
    )
    admin = filters.CharFilter(
        field_name='admin__username',
        lookup_expr='icontains'
    )
    created_on = filters.CharFilter(
        field_name='created_on__date',
        lookup_expr='exact'
    )
    updated_on = filters.CharFilter(
        field_name='updated_on__date',
        lookup_expr='exact'
    )

    class Meta:
        model = Client
        fields = [
            'id',
            'admin',
            'client_name',
            'created_on',
            'updated_on',
        ]
