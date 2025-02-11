from django.shortcuts import render

def home(request):
    return render(request, 'setoo_app/home.html')