from django.contrib import admin

from .models import User, ResetPassword, Client, UnitOfHistory

admin.site.register(User)
admin.site.register(Client)
admin.site.register(ResetPassword)
admin.site.register(UnitOfHistory)
