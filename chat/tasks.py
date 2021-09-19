from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

from mysite.celery import app


@app.task
def send_email(email):
    send_mail('hi', "hello everyone", settings.DEFAULT_FROM_EMAIL, [email])
