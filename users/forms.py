from django import forms
from django.contrib.auth import get_user_model

from .models import Client

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ("username", "email", "password")


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ("username", "email", "password")


class ClientForm(forms.ModelForm):

    class Meta:
        model = Client
        exclude = ('auth_key', 'admin', 'employee', 'block_offensive_word', 'restrict_re_format')


class ClientEmployeeForm(forms.ModelForm):

    class Meta:
        model = Client
        fields = ('employee', )
