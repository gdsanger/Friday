"""
Project views for Friday project.
"""
import json
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from .models import Project, ProjectUserMembership, ProjectTeamMembership
from apps.teams.models import Team
from apps.tasks.models import Task

User = get_user_model()


class ProjectListView(LoginRequiredMixin, ListView):
    template_name = 'projects/list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        # Show projects the user is a member of + org-visible projects
        user = self.request.user
        my_teams = user.teams

        # Check if user is in any global team
        is_global_member = my_teams.filter(is_global=True).exists()

        if is_global_member:
            # Global team members see ALL projects (since global teams are members of all projects)
            queryset = Project.objects.all()
        else:
            # Regular users see: their projects + team projects + org-visible
            queryset = Project.objects.filter(
                models.Q(user_members=user) |
                models.Q(team_members__in=my_teams) |
                models.Q(visibility='organisation')
            ).distinct()

        queryset = queryset.annotate(
            task_count=Count('tasks'),
            open_task_count=Count('tasks', filter=~models.Q(tasks__status='done')),
            done_task_count=Count('tasks', filter=models.Q(tasks__status='done')),
        ).order_by('-updated_at')

        # Filter by status if provided
        status_filter = self.request.GET.get('status', 'active')
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        ctx = super().get_context_data(**kwargs)
        # Filter by status tab
        ctx['status_filter'] = self.request.GET.get('status', 'active')
        ctx['status_choices'] = Project.STATUS_CHOICES
        ctx['today'] = timezone.now().date()
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/detail.html'

    def dispatch(self, request, *args, **kwargs):
        project = self.get_object()
        if not (project.is_member(request.user) or project.visibility == 'organisation'):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        ctx['tasks_by_status'] = {
            status: project.tasks.filter(status=status).count()
            for status, _ in Task.STATUS_CHOICES
        }
        ctx['recent_tasks'] = project.tasks.exclude(
            status='done'
        ).select_related(
            'assigned_to_user', 'assigned_to_team'
        ).order_by('priority', 'due_date')[:10]
        ctx['user_memberships']  = project.projectusermembership_set.select_related('user')
        ctx['team_memberships']  = project.projectteammembership_set.select_related('team')
        ctx['available_users']   = User.objects.filter(is_active=True).exclude(
            projectusermembership__project=project
        )
        ctx['available_teams']   = Team.objects.filter(is_active=True).exclude(
            projectteammembership__project=project
        ).exclude(is_global=True)  # Exclude global teams from "add team" dropdown
        ctx['global_teams']      = Team.objects.filter(is_global=True, is_active=True)
        ctx['user_role'] = project.get_effective_role(self.request.user)
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'projects/form.html'
    fields = ['name', 'description', 'status', 'visibility',
              'start_date', 'due_date', 'priority', 'color']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Project.STATUS_CHOICES
        ctx['visibility_choices'] = Project.VISIBILITY_CHOICES
        ctx['priority_choices'] = [
            (0, 'None'), (1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical')
        ]
        return ctx

    def form_valid(self, form):
        project = form.save(commit=False)
        project.owner = self.request.user
        project.save()
        # Auto-add creator as manager
        ProjectUserMembership.objects.create(
            project=project, user=self.request.user, role='manager'
        )
        return redirect('projects:project-detail', pk=project.pk)


class ProjectEditView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = 'projects/form.html'
    fields = ['name', 'description', 'status', 'visibility',
              'start_date', 'due_date', 'priority', 'color']

    def dispatch(self, request, *args, **kwargs):
        project = self.get_object()
        role = project.get_effective_role(request.user)
        if role != 'manager' and not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Project.STATUS_CHOICES
        ctx['visibility_choices'] = Project.VISIBILITY_CHOICES
        ctx['priority_choices'] = [
            (0, 'None'), (1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical')
        ]
        return ctx

    def get_success_url(self):
        return reverse('projects:project-detail', kwargs={'pk': self.object.pk})


class ProjectArchiveView(LoginRequiredMixin, View):
    """HTMX — toggles archive status, returns updated status badge."""
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.status = 'archived' if project.status != 'archived' else 'active'
        project.save(update_fields=['status'])
        return render(request, 'projects/partials/status_badge.html', {'project': project})


class ProjectAddUserView(LoginRequiredMixin, View):
    """HTMX — add user to project, return updated member list."""
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        user_id = request.POST.get('user_id')
        role    = request.POST.get('role', 'contributor')
        ProjectUserMembership.objects.get_or_create(
            project=project, user_id=user_id, defaults={'role': role}
        )
        return render(request, 'projects/partials/member_list.html',
                      self._member_ctx(project))

    def _member_ctx(self, project):
        return {
            'project': project,
            'user_memberships': project.projectusermembership_set.select_related('user'),
            'team_memberships': project.projectteammembership_set.select_related('team'),
        }


class ProjectAddTeamView(LoginRequiredMixin, View):
    """HTMX — add team to project, return updated member list."""
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        team_id = request.POST.get('team_id')
        role    = request.POST.get('role', 'contributor')
        ProjectTeamMembership.objects.get_or_create(
            project=project, team_id=team_id, defaults={'role': role}
        )
        return render(request, 'projects/partials/member_list.html',
                      self._member_ctx(project))

    def _member_ctx(self, project):
        return {
            'project': project,
            'user_memberships': project.projectusermembership_set.select_related('user'),
            'team_memberships': project.projectteammembership_set.select_related('team'),
        }


class ProjectRemoveUserView(LoginRequiredMixin, View):
    """HTMX — remove user from project, return updated member list."""
    def post(self, request, pk, user_id):
        project = get_object_or_404(Project, pk=pk)
        ProjectUserMembership.objects.filter(project=project, user_id=user_id).delete()
        return render(request, 'projects/partials/member_list.html',
                      self._member_ctx(project))

    def _member_ctx(self, project):
        return {
            'project': project,
            'user_memberships': project.projectusermembership_set.select_related('user'),
            'team_memberships': project.projectteammembership_set.select_related('team'),
        }


class ProjectRemoveTeamView(LoginRequiredMixin, View):
    """HTMX — remove team from project, return updated member list."""
    def post(self, request, pk, team_id):
        project = get_object_or_404(Project, pk=pk)
        ProjectTeamMembership.objects.filter(project=project, team_id=team_id).delete()
        return render(request, 'projects/partials/member_list.html',
                      self._member_ctx(project))

    def _member_ctx(self, project):
        return {
            'project': project,
            'user_memberships': project.projectusermembership_set.select_related('user'),
            'team_memberships': project.projectteammembership_set.select_related('team'),
        }


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendar/Gantt view for projects."""
    template_name = 'projects/calendar.html'


class CalendarDataView(LoginRequiredMixin, View):
    """
    Returns JSON data for DHTMLX Gantt.
    Format: { data: [...tasks/projects], links: [...dependencies] }

    Gantt "tasks" = both projects (as parent bars) and task deadlines (as milestones).
    Gantt "resources" = assigned users and teams.
    """
    def get(self, request):
        user = request.user
        my_teams = user.teams

        # Accessible projects
        projects = Project.objects.filter(
            models.Q(user_members=user) |
            models.Q(team_members__in=my_teams) |
            models.Q(visibility='organisation')
        ).exclude(status='archived').distinct()

        gantt_tasks = []
        gantt_links = []
        gantt_resources = []
        resource_ids = set()

        for project in projects:
            start = project.start_date or project.created_at.date()
            end = project.due_date

            if not end:
                continue  # skip projects with no end date

            # Project bar
            gantt_tasks.append({
                'id': f'p_{project.pk}',
                'text': project.name,
                'start_date': start.strftime('%Y-%m-%d'),
                'end_date': end.strftime('%Y-%m-%d'),
                'color': project.color,
                'type': 'project',
                'open': True,
                'readonly': False,
                'project_id': project.pk,
            })

            # Task deadlines as milestones (children of project bar)
            tasks = project.tasks.filter(
                deadline__isnull=False
            ).select_related('assigned_to_user', 'assigned_to_team')

            for task in tasks:
                # Determine resource
                resource_id = None
                resource_label = None

                if task.assigned_to_user:
                    resource_id = f'u_{task.assigned_to_user.pk}'
                    resource_label = task.assigned_to_user.full_name
                    if resource_id not in resource_ids:
                        gantt_resources.append({
                            'id': resource_id,
                            'label': resource_label,
                            'avatar': task.assigned_to_user.initials,
                        })
                        resource_ids.add(resource_id)

                elif task.assigned_to_team:
                    resource_id = f't_{task.assigned_to_team.pk}'
                    resource_label = task.assigned_to_team.name
                    if resource_id not in resource_ids:
                        gantt_resources.append({
                            'id': resource_id,
                            'label': resource_label,
                            'color': task.assigned_to_team.color,
                        })
                        resource_ids.add(resource_id)

                gantt_tasks.append({
                    'id': f't_{task.pk}',
                    'text': task.title,
                    'start_date': task.deadline.strftime('%Y-%m-%d'),
                    'duration': 0,  # milestone = duration 0
                    'type': 'milestone',
                    'parent': f'p_{project.pk}',
                    'priority': task.priority,
                    'status': task.status,
                    'resource_id': resource_id,
                    'resource_label': resource_label,
                    'task_id': task.pk,
                })

        return JsonResponse({
            'data': gantt_tasks,
            'links': gantt_links,
            'resources': gantt_resources,
        })


class CalendarUpdateView(LoginRequiredMixin, View):
    """
    HTMX/AJAX — update project dates after drag & drop in Gantt.
    POST: { type: 'project', id: pk, start_date: '...', end_date: '...' }
    """
    def post(self, request):
        data = json.loads(request.body)
        obj_type = data.get('type')
        obj_id = data.get('id')
        start_str = data.get('start_date')
        end_str = data.get('end_date')

        fmt = '%Y-%m-%d'

        if obj_type == 'project':
            project = get_object_or_404(Project, pk=obj_id)
            if not (project.get_effective_role(request.user) == 'manager'
                    or request.user.is_staff):
                raise PermissionDenied
            if start_str:
                project.start_date = datetime.strptime(start_str, fmt).date()
            if end_str:
                project.due_date = datetime.strptime(end_str, fmt).date()
            project.save(update_fields=['start_date', 'due_date'])

        return JsonResponse({'status': 'ok'})
