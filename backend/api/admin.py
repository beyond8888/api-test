from django.contrib import admin

from .models import Collection, Environment, HistoryEntry


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(HistoryEntry)
class HistoryEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'timestamp']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
