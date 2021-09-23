from __future__ import absolute_import, unicode_literals

from django.core.mail import send_mail
from django.conf import settings

from mysite.celery import app
from mysite.mail import send_mail, send_mail_from_template


@app.task
def send_email_on_delay(template, context, subject, email):
    """
        send or process email by actual template
    """
    print("delay")
    send_mail_from_template(template, context, subject, email)


@app.task
def send_password_reset_mail(email, token):
    """
        send mail including a link for reset password
    """
    print("reset password")
    url = f"{settings.SITE_URL}/reset-password?email={email}&token={token}"
    SUBJECT = "Reset Password Request"
    # The HTML body of the email.
    body = """
    <html>
    <head></head>
    <body>
      <p>Here is your password reset link:</p>
      <p><a href='{0}'>{1}</a></p>
    </body>
    </html>
    """.format(url, url)
    send_mail(SUBJECT, body, email)
