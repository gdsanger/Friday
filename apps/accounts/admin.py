"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin."""
    list_display = ['username', 'email', 'display_name', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('avatar', 'display_name', 'job_title', 'phone')}),
        ('Azure SSO', {'fields': ('azure_oid', 'azure_upn')}),
        ('Preferences', {'fields': ('notify_email', 'notify_inapp', 'theme', 'timezone')}),
    )
