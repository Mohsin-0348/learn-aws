from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from learn_pro.mail import send_mail


# @login_required
def hello(request):
    context = {}
    if request.GET.get('viewer'):
        context['viewer'] = request.GET['viewer']
        send_mail('Hello', "This is a test mail", request.GET['viewer'])
    return render(request, 'hello.html', context)
