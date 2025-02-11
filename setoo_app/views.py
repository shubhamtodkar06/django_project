from django.shortcuts import render

def home(request):
    print('helloworld')
    return render(request, 'setoo_app/home.html')
