"""
Admin configuration for tasks app.
"""
from django.contrib import admin
from .models import (
    Label, Task, Comment, Attachment, TimeEntry, TaskTemplate,
    ChecklistTemplate, ChecklistTemplateItem, TaskChecklistItem
)


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    """TaskTemplate admin."""
    list_display = ['name', 'slug', 'default_project', 'is_active', 'is_portal_visible', 'client', 'created_at']
    list_filter = ['is_active', 'is_portal_visible', 'client', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = []


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


class ChecklistTemplateItemInline(admin.TabularInline):
    """Inline for ChecklistTemplateItem."""
    model = ChecklistTemplateItem
    extra = 1
    fields = ['title', 'order']
    ordering = ['order']


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    """ChecklistTemplate admin."""
    list_display = ['name', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ChecklistTemplateItemInline]


@admin.register(TaskChecklistItem)
class TaskChecklistItemAdmin(admin.ModelAdmin):
    """TaskChecklistItem admin."""
    list_display = ['task', 'title', 'is_done', 'order', 'done_by', 'done_at']
    list_filter = ['is_done', 'created_at']
    search_fields = ['title', 'task__title']
    readonly_fields = ['created_at', 'updated_at']
