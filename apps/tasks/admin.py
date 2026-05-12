"""
Admin configuration for tasks app.
"""
from django.contrib import admin
from .models import Label, Task, Comment, Attachment, TimeEntry


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    """Label admin."""
    list_display = ['name', 'color']
    search_fields = ['name']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Task admin."""
    list_display = ['title', 'project', 'status', 'priority', 'assigned_to_user', 'assigned_to_team', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'created_at', 'due_date']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    filter_horizontal = ['labels', 'watching_users', 'watching_teams']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Comment admin."""
    list_display = ['task', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body', 'task__title', 'author__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Attachment admin."""
    list_display = ['filename', 'task', 'uploaded_by', 'size_bytes', 'created_at']
    list_filter = ['created_at']
    search_fields = ['filename', 'task__title']
    readonly_fields = ['created_at']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    """Time Entry admin."""
    list_display = ['task', 'user', 'started_at', 'ended_at', 'duration_m']
    list_filter = ['started_at', 'user']
    search_fields = ['task__title', 'user__username', 'note']
    readonly_fields = ['created_at', 'updated_at']
