"""
Admin configuration for core app.
"""
from django.contrib import admin
from .models import Organisation


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    """Organisation admin."""
    list_display = ['name', 'slug', 'website', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
