from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('apps/', views.apps, name='apps'),
    path('apps/category/<str:category_name>/', views.apps, name='apps_by_category'),
    path('apps/<str:fap_id>/', views.app, name='app'),
    path("apps/<str:fap_id>/upload/", views.upload, name='upload_app'),
]