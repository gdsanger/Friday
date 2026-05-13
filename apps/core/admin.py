"""
Admin configuration for core app.
"""
from django.contrib import admin
from .models import Organisation, Client


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    """Organisation admin."""
    list_display = ['name', 'slug', 'website', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Client admin."""
    list_display = ['name', 'short_name', 'slug', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'short_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

