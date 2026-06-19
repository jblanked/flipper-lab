from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin

from .models import App, Category, SyncRun

@admin.register(App)
class AppAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'author', 'category', 'version')
    search_fields = ('name', 'author', 'category__name')
    list_filter = ('category',)

@admin.register(Category)
class CategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'finished_at', 'total_processed')
    list_filter = ('status',)
    readonly_fields = ('id', 'status', 'started_at', 'finished_at', 'error_message', 'total_processed')
