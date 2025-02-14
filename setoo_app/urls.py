# django_project/setoo_app/urls.py
from django.urls import path
from. import views
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect  

urlpatterns = [
    path('get_api_key/', views.get_api_key, name='get_api_key'),
    path('manage_files/', views.manage_files, name='manage_files'),
    # ... any other URL patterns for your app
]