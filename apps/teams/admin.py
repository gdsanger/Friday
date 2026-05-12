"""
Admin configuration for teams app.
"""
from django.contrib import admin
from .models import Team, TeamMembership


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Team admin."""
    list_display = ['name', 'slug', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    """Team Membership admin."""
    list_display = ['user', 'team', 'role', 'joined_at']
    list_filter = ['role', 'team', 'joined_at']
    search_fields = ['user__username', 'user__email', 'team__name']
    readonly_fields = ['joined_at', 'created_at', 'updated_at']
