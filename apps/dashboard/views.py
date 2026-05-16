"""
Dashboard views.
"""
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.tasks.models import Task
from apps.projects.models import Project
from apps.notifications.models import Notification
from apps.core.models import Client, CapacityBudget


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

        # Calculate percentage for each project
        for project in projects:
            if project.total_tasks > 0:
                project.pct = int((project.done_tasks / project.total_tasks) * 100)
            else:
                project.pct = 0

        status_counts = projects.values('status').annotate(n=Count('id'))

        return render(request, 'dashboard/partials/widget_project_status.html', {
            'projects': projects,
            'status_counts': {s['status']: s['n'] for s in status_counts},
        })


class WidgetActivityView(LoginRequiredMixin, View):
    """
    Dashboard Widget — globaler Activity Feed.
    Zeigt die letzten 20 Aktivitäten auf Tasks die
    der User sehen darf.
    """
    def get(self, request):
        from apps.tasks.models import TaskActivity
        user     = request.user
        my_teams = user.teams

        # Nur Aktivitäten auf zugänglichen Tasks
        activities = TaskActivity.objects.filter(
            models.Q(task__project__user_members=user) |
            models.Q(task__project__team_members__in=my_teams)
        ).select_related(
            'user', 'task', 'task__project'
        ).distinct().order_by('-created_at')[:20]

        return render(request, 'dashboard/partials/widget_activity.html', {
            'activities': activities,
        })


class WidgetDueWeekView(LoginRequiredMixin, View):
    """KPI widget showing count of tasks due this week (7 days)."""
    def get(self, request):
        today = timezone.now().date()
        in_7days = today + timedelta(days=7)
        user = request.user
        my_teams = user.teams

        count = Task.objects.filter(
            Q(assigned_to_user=user) | Q(assigned_to_team__in=my_teams),
            due_date__range=(today, in_7days),
        ).exclude(status='done').count()

        return render(request, 'dashboard/partials/widget_due_week.html', {
            'count': count,
        })


class WidgetMyProjectsView(LoginRequiredMixin, View):
    """KPI widget showing count of user's active projects."""
    def get(self, request):
        user = request.user
        my_teams = user.teams

        count = Project.objects.filter(
            Q(user_members=user) | Q(team_members__in=my_teams)
        ).exclude(status='archived').distinct().count()

        return render(request, 'dashboard/partials/widget_my_projects.html', {
            'count': count,
        })


class WidgetCapacityView(LoginRequiredMixin, View):
    """
    Shows SP budget vs. planned SP per client for the current week.
    Only shown for staff users or team leads.
    """
    def get(self, request):
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        user = request.user
        my_teams = user.teams

        capacity_data = []

        for client in Client.objects.filter(is_active=True):
            client_data = {'client': client, 'teams': []}
            total_budget = Decimal('0')
            total_planned = Decimal('0')

            for team in my_teams:
                budget = CapacityBudget.current_budget(client, team, today)
                if not budget:
                    continue

                # Planned SP: tasks assigned to this team for this client
                # excluding done tasks
                planned = Task.objects.filter(
                    models.Q(client=client) |
                    models.Q(project__client=client),
                    assigned_to_team=team,
                    story_points__isnull=False,
                ).exclude(status=Task.STATUS_DONE).aggregate(
                    total=Sum('story_points')
                )['total'] or Decimal('0')

                weekly_budget = budget.weekly_sp_budget
                total_budget += weekly_budget
                total_planned += planned

                client_data['teams'].append({
                    'team': team,
                    'budget': weekly_budget,
                    'planned': planned,
                    'pct': min(int((planned / weekly_budget * 100) if weekly_budget > 0 else 0), 100),
                    'over': planned > weekly_budget,
                })

            if client_data['teams']:
                client_data['total_budget'] = total_budget
                client_data['total_planned'] = total_planned
                capacity_data.append(client_data)

        return render(request, 'dashboard/partials/widget_capacity.html', {
            'capacity_data': capacity_data,
            'week_start': week_start,
            'week_end': week_end,
        })
