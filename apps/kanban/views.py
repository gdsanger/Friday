"""
Kanban board views for Friday project.
"""
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import render
from django.views import View

from apps.tasks.models import Task
from apps.projects.models import Project
from apps.teams.models import Team


class KanbanBoardView(LoginRequiredMixin, View):
    """
    Cross-project Kanban board view.
    Shows tasks across all accessible projects in 5 status columns.
    Supports view modes and multiple filters.
    """
    def get(self, request):
        user     = request.user
        my_teams = Team.objects.filter(memberships__user=user)

        # Base queryset: all tasks in accessible projects
        accessible_projects = Project.objects.filter(
            models.Q(user_members=user) |
            models.Q(team_members__in=my_teams) |
            models.Q(visibility='organisation')
        ).distinct()

        tasks = Task.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'project', 'assigned_to_user', 'assigned_to_team', 'created_by'
        ).prefetch_related('labels').order_by('position', '-created_at')

        # ── View mode filter ──────────────────────────────────
        view_mode = request.GET.get('view', 'all')

        if view_mode == 'mine_created':
            tasks = tasks.filter(created_by=user)

        elif view_mode == 'mine_assigned':
            tasks = tasks.filter(assigned_to_user=user)

        elif view_mode == 'team_assigned':
            tasks = tasks.filter(assigned_to_team__in=my_teams)

        elif view_mode == 'watching':
            tasks = tasks.filter(
                models.Q(watching_users=user) |
                models.Q(watching_teams__in=my_teams)
            ).distinct()

        # ── Additional filters ────────────────────────────────
        if project_id := request.GET.get('project'):
            tasks = tasks.filter(project_id=project_id)

        if team_id := request.GET.get('team'):
            tasks = tasks.filter(
                models.Q(assigned_to_team_id=team_id) |
                models.Q(assigned_to_user__team_memberships__team_id=team_id)
            ).distinct()

        if client_id := request.GET.get('client'):
            tasks = tasks.filter(
                models.Q(client_id=client_id) |
                models.Q(project__client_id=client_id)
            )

        if priority := request.GET.get('priority'):
            tasks = tasks.filter(priority=priority)

        if due := request.GET.get('due'):
            from django.utils import timezone
            if due == 'overdue':
                tasks = tasks.filter(
                    due_date__lt=timezone.now().date()
                ).exclude(status='done')
            elif due == 'today':
                tasks = tasks.filter(due_date=timezone.now().date())
            elif due == 'week':
                tasks = tasks.filter(
                    due_date__lte=timezone.now().date() + timedelta(days=7)
                )

        if assignee_id := request.GET.get('assignee'):
            tasks = tasks.filter(assigned_to_user_id=assignee_id)

        # Label filter (ISSUE-62)
        if label_id := request.GET.get('label'):
            tasks = tasks.filter(labels__pk=label_id)

        # ── Subtask filter ────────────────────────────────────────
        show_subtasks = request.GET.get('show_subtasks', '')
        if not show_subtasks:
            # Default: hide subtasks — show only top-level tasks
            tasks = tasks.filter(parent_task__isnull=True)

        # ── Build columns ─────────────────────────────────────
        columns = {status: [] for status, _ in Task.STATUS_CHOICES}
        for task in tasks:
            columns[task.status].append(task)

        from apps.core.models import Client
        from django.contrib.auth import get_user_model
        from apps.tasks.models import Label
        User = get_user_model()

        ctx = {
            'columns':        columns,
            'status_choices': Task.STATUS_CHOICES,
            'view_mode':      view_mode,
            'projects':       accessible_projects.order_by('name'),
            'teams':          Team.objects.filter(is_active=True),
            'clients':        Client.objects.filter(is_active=True).order_by('name'),
            'priority_choices': Task.PRIORITY_CHOICES,
            'assignees':      User.objects.filter(
                is_active=True,
                is_portal_user=False,
            ).order_by('display_name', 'username'),
            'labels':         Label.objects.annotate(
                task_count=models.Count('task')
            ).filter(task_count__gt=0).order_by('name'),
            'active_filters': {
                'project':  request.GET.get('project', ''),
                'team':     request.GET.get('team', ''),
                'client':   request.GET.get('client', ''),
                'priority': request.GET.get('priority', ''),
                'due':      request.GET.get('due', ''),
                'assignee': request.GET.get('assignee', ''),
                'label':    request.GET.get('label', ''),
                'show_subtasks': request.GET.get('show_subtasks', ''),
            },
        }

        # HTMX partial refresh (filter change) vs. full page load
        if request.htmx:
            return render(request, 'kanban/partials/board.html', ctx)
        return render(request, 'kanban/board.html', ctx)
