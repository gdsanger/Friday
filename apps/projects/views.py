"""
Project views for Friday project.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

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
        queryset = Project.objects.filter(
            models.Q(user_members=user) |
            models.Q(team_members__in=my_teams) |
            models.Q(visibility='organisation')
        ).distinct().annotate(
            task_count=Count('tasks'),
            open_task_count=Count('tasks', filter=~models.Q(tasks__status='done')),
        ).order_by('-updated_at')

        # Filter by status if provided
        status_filter = self.request.GET.get('status', 'active')
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Filter by status tab
        ctx['status_filter'] = self.request.GET.get('status', 'active')
        ctx['status_choices'] = Project.STATUS_CHOICES
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
        )
        ctx['user_role'] = project.get_effective_role(self.request.user)
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'projects/form.html'
    fields = ['name', 'description', 'status', 'visibility',
              'start_date', 'due_date', 'priority', 'color']

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
