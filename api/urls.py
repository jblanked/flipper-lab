from django.urls import path
from . import views

urlpatterns = [
    path("apps/", views.app_list, name="app-list"),
    path("apps/<int:app_id>/", views.app_detail, name="app-detail"),
    path("apps/<int:app_id>/download/", views.app_download, name="app-download"),
    path("categories/", views.category_list, name="category-list"),
    path("new/app/", views.new_app, name="new-app"),
    path("new/category/", views.new_category, name="new-category"),
    path("sync/", views.sync_manifests, name="sync-manifests"),
    path("sync/stop/", views.sync_stop, name="sync-stop"),
]