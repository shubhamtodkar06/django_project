# django_project/setoo_app/urls.py
from django.urls import path
from. import views

urlpatterns = [
    path('get_api_key/', views.get_api_key, name='get_api_key'),
    path('manage_files/', views.manage_files, name='manage_files'),
    path('analysis_results/<int:results_id>/', views.analysis_results, name='analysis_results'),
    path('display_top_resumes/<int:results_id>/', views.display_top_resumes, name='display_top_resumes'),
]