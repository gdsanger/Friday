"""
Admin configuration for ai app.
"""
from django.contrib import admin
from .models import AIProviderConfig, AIGlobalSettings, AIUsageLog


@admin.register(AIProviderConfig)
class AIProviderConfigAdmin(admin.ModelAdmin):
    """AI Provider Config admin."""
    list_display = ['provider', 'model_name', 'is_active', 'rpm_limit', 'tpm_limit', 'updated_at']
    list_filter = ['provider', 'is_active']
    readonly_fields = ['updated_at']


@admin.register(AIGlobalSettings)
class AIGlobalSettingsAdmin(admin.ModelAdmin):
    """AI Global Settings admin."""
    list_display = ['default_provider', 'is_enabled', 'monthly_token_budget', 'per_user_daily_limit']


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    """AI Usage Log admin."""
    list_display = ['user', 'team', 'provider', 'action', 'total_tokens', 'success', 'created_at']
    list_filter = ['provider', 'success', 'created_at']
    search_fields = ['user__username', 'team__name', 'action', 'object_type']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
