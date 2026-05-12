"""
Admin configuration for projects app.
"""
from django.contrib import admin
from .models import Project, ProjectUserMembership, ProjectTeamMembership


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Project admin."""
    list_display = ['name', 'status', 'visibility', 'owner', 'start_date', 'due_date', 'created_at']
    list_filter = ['status', 'visibility', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(ProjectUserMembership)
class ProjectUserMembershipAdmin(admin.ModelAdmin):
    """Project User Membership admin."""
    list_display = ['user', 'project', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'user__email', 'project__name']
    readonly_fields = ['joined_at']


@admin.register(ProjectTeamMembership)
class ProjectTeamMembershipAdmin(admin.ModelAdmin):
    """Project Team Membership admin."""
    list_display = ['team', 'project', 'role', 'added_at']
    list_filter = ['role', 'added_at']
    search_fields = ['team__name', 'project__name']
    readonly_fields = ['added_at']
