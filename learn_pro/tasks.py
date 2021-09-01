
from django.conf import settings

from learn_pro.celery import app
from learn_pro.mail import send_mail


@app.task
def send_hello_mail(email):
    """
        send mail including a link for reset password
    """
    url = f"/hello/"
    SUBJECT = "New mail request"
    # The HTML body of the email.
    body = """
    <html>
    <head></head>
    <body>
      <p>Here is your new route link:</p>
      <p><a href='{0}'>{1}</a></p>
    </body>
    </html>
    """.format(url, url)
    send_mail(SUBJECT, body, email)
