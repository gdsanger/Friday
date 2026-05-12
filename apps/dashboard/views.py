"""
Dashboard views.
"""
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.tasks.models import Task
from apps.projects.models import Project
from apps.notifications.models import Notification


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard home page - renders shell only, widgets load via HTMX."""
    template_name = 'dashboard/dashboard.html'


class WidgetMyTasksView(LoginRequiredMixin, View):
    """Widget showing count of open tasks assigned to current user."""
    def get(self, request):
        tasks = Task.objects.filter(
            assigned_to_user=request.user
        ).exclude(status='done').select_related('project').order_by('due_date', '-priority')
        return render(request, 'dashboard/partials/widget_my_tasks.html', {
            'tasks': tasks,
            'count': tasks.count(),
        })


class WidgetOverdueView(LoginRequiredMixin, View):
    """Widget showing overdue tasks for user and their teams."""
    def get(self, request):
        today = timezone.now().date()
        user = request.user
        my_teams = user.teams

        overdue = Task.objects.filter(
            Q(assigned_to_user=user) | Q(assigned_to_team__in=my_teams),
            due_date__lt=today,
        ).exclude(status='done').select_related('project', 'assigned_to_team')

        return render(request, 'dashboard/partials/widget_overdue.html', {
            'tasks': overdue,
            'count': overdue.count(),
        })


class WidgetTeamLoadView(LoginRequiredMixin, View):
    """Widget showing open task counts per team."""
    def get(self, request):
        my_teams = request.user.teams
        team_data = []
        for team in my_teams:
            open_count = Task.objects.filter(
                assigned_to_team=team
            ).exclude(status='done').count()
            team_data.append({'team': team, 'open': open_count})

        # Calculate max for progress bar scaling
        max_open = max([t['open'] for t in team_data], default=1)
        for t in team_data:
            t['max_open'] = max_open

        return render(request, 'dashboard/partials/widget_team_load.html', {
            'team_data': team_data,
        })


class WidgetDueSoonView(LoginRequiredMixin, View):
    """Widget showing tasks due in the next 7 days."""
    def get(self, request):
        today = timezone.now().date()
        in_7days = today + timedelta(days=7)
        user = request.user
        my_teams = user.teams

        due_soon = Task.objects.filter(
            Q(assigned_to_user=user) | Q(assigned_to_team__in=my_teams),
            due_date__range=(today, in_7days),
        ).exclude(status='done').select_related(
            'project', 'assigned_to_team', 'assigned_to_user'
        ).order_by('due_date')

        return render(request, 'dashboard/partials/widget_due_soon.html', {
            'tasks': due_soon,
            'today': today,
        })


class WidgetProjectStatusView(LoginRequiredMixin, View):
    """Widget showing project status and progress."""
    def get(self, request):
        user = request.user
        my_teams = user.teams

        projects = Project.objects.filter(
            Q(user_members=user) | Q(team_members__in=my_teams)
        ).exclude(status='archived').distinct().annotate(
            total_tasks=Count('tasks'),
            done_tasks=Count('tasks', filter=Q(tasks__status='done')),
        ).order_by('status', '-updated_at')[:12]

        status_counts = projects.values('status').annotate(n=Count('id'))

        return render(request, 'dashboard/partials/widget_project_status.html', {
            'projects': projects,
            'status_counts': {s['status']: s['n'] for s in status_counts},
        })


class WidgetActivityView(LoginRequiredMixin, View):
    """Widget showing recent activity notifications."""
    def get(self, request):
        # Most recent notifications for this user
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('actor').order_by('-created_at')[:20]

        return render(request, 'dashboard/partials/widget_activity.html', {
            'notifications': notifications,
        })
