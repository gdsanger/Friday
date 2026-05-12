"""
Admin configuration for mail models.
"""
from django.contrib import admin
from .models import UserMailToken, MailThread, WebhookSubscription


@admin.register(UserMailToken)
class UserMailTokenAdmin(admin.ModelAdmin):
    """Admin interface for UserMailToken."""
    list_display = ['user', 'expires_at', 'updated_at', 'is_expired']
    list_filter = ['expires_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['updated_at']
    raw_id_fields = ['user']

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


@admin.register(MailThread)
class MailThreadAdmin(admin.ModelAdmin):
    """Admin interface for MailThread."""
    list_display = ['subject', 'direction', 'task', 'sender_email', 'received_at', 'created_at']
    list_filter = ['direction', 'received_at', 'created_at']
    search_fields = ['subject', 'sender_email', 'sender_name', 'body_preview']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['task']
    date_hierarchy = 'created_at'


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    """Admin interface for WebhookSubscription."""
    list_display = ['user', 'subscription_id', 'resource', 'expiration', 'created_at']
    list_filter = ['expiration', 'created_at']
    search_fields = ['user__username', 'subscription_id', 'resource']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
    date_hierarchy = 'expiration'
