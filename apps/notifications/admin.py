"""
Admin configuration for notifications app.
"""
from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification admin."""
    list_display = ['recipient', 'verb', 'actor', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['recipient__username', 'actor__username', 'verb']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
