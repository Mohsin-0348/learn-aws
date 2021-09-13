
from django.http import HttpResponse
from django.views.generic import View
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailVerify(View):

    def get(self, request, token):
        if token:
            try:
                user = User.objects.get(activation_token=token)
                user.activation_token = None
                user.is_email_verified = True
                user.save()
                return HttpResponse("<center><h2>Verified Successful</h2></center>")
            except User.DoesNotExist:
                return HttpResponse("<center><h2>Invalid or expired token!</h2></center>")

