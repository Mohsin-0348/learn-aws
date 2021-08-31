from django.shortcuts import render, HttpResponse


def hello(request):
    return HttpResponse("<center><h1>Hello World</h1></center>")
