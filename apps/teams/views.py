"""
Team views for Friday project.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.text import slugify
from django.views import View
from django.views.generic import ListView, DetailView

from .models import Team, TeamMembership

User = get_user_model()


class StaffRequiredMixin(LoginRequiredMixin):
    """Restrict view to staff users only."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'teams/list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        return Team.objects.filter(is_active=True).annotate(
            member_count=Count('memberships'),
            project_count=Count('member_projects', distinct=True),
        ).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['my_teams'] = self.request.user.teams
        return ctx


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['memberships'] = self.object.memberships.select_related('user').order_by('role', 'user__display_name')

        # Active projects this team is already assigned to
        ctx['projects'] = self.object.member_projects.exclude(
            status='archived'
        ).order_by('-updated_at')

        # Projects this team is NOT yet assigned to (for the assign form)
        from apps.projects.models import Project
        ctx['available_projects'] = Project.objects.exclude(
            status='archived'
        ).exclude(
            team_members=self.object
        ).order_by('name')

        ctx['all_users'] = User.objects.filter(is_active=True).exclude(
            team_memberships__team=self.object
        ).order_by('display_name')
        ctx['is_lead'] = self.object.memberships.filter(
            user=self.request.user, role='lead'
        ).exists()
        return ctx


class TeamMemberAddView(LoginRequiredMixin, View):
    """HTMX — returns updated member list partial."""
    def post(self, request, slug):
        team = get_object_or_404(Team, slug=slug)
        user_id = request.POST.get('user_id')
        role    = request.POST.get('role', 'member')
        user    = get_object_or_404(User, pk=user_id)
        TeamMembership.objects.get_or_create(
            team=team, user=user, defaults={'role': role}
        )
        memberships = team.memberships.select_related('user').order_by('role', 'user__display_name')
        return render(request, 'teams/partials/member_list.html',
                      {'team': team, 'memberships': memberships})


class TeamMemberRemoveView(LoginRequiredMixin, View):
    """HTMX — returns updated member list partial."""
    def post(self, request, slug, user_id):
        team = get_object_or_404(Team, slug=slug)
        TeamMembership.objects.filter(team=team, user_id=user_id).delete()
        memberships = team.memberships.select_related('user').order_by('role', 'user__display_name')
        return render(request, 'teams/partials/member_list.html',
                      {'team': team, 'memberships': memberships})


class TeamMemberRoleView(LoginRequiredMixin, View):
    """HTMX — inline role change, returns single row partial."""
    def post(self, request, slug, user_id):
        team = get_object_or_404(Team, slug=slug)
        role = request.POST.get('role')
        TeamMembership.objects.filter(team=team, user_id=user_id).update(role=role)
        membership = team.memberships.select_related('user').get(user_id=user_id)
        return render(request, 'teams/partials/member_row.html',
                      {'team': team, 'membership': membership})


class TeamEditView(LoginRequiredMixin, View):
    """
    Only Team Leads and staff users can edit a team.
    GET  → render edit form
    POST → save changes, redirect to team detail
    """
    def dispatch(self, request, *args, **kwargs):
        self.team = get_object_or_404(Team, slug=kwargs['slug'])
        is_lead = self.team.memberships.filter(
            user=request.user, role='lead'
        ).exists()
        if not (is_lead or request.user.is_staff):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug):
        return render(request, 'teams/edit.html', {'team': self.team})

    def post(self, request, slug):
        team = self.team
        team.name = request.POST.get('name', team.name).strip()
        team.description = request.POST.get('description', team.description).strip()
        team.color = request.POST.get('color', team.color).strip()
        team.icon = request.POST.get('icon', team.icon).strip()
        team.is_global = 'is_global' in request.POST

        # Validate: name must not be empty
        if not team.name:
            return render(request, 'teams/edit.html', {
                'team': team,
                'error': 'Team name cannot be empty.'
            })

        # Regenerate slug only if name changed
        new_slug = slugify(team.name)
        if new_slug != team.slug and not Team.objects.filter(slug=new_slug).exists():
            team.slug = new_slug

        team.save()
        return redirect('teams:team-detail', slug=team.slug)


class TeamCreateView(StaffRequiredMixin, View):
    """
    GET  → render create form
    POST → create team, redirect to team detail
    """
    def get(self, request):
        return render(request, 'teams/create.html', {
            'color_presets': [
                '#6366f1', '#2d6a4f', '#e07c24', '#2980b9',
                '#8e44ad', '#c0392b', '#16a085', '#d35400',
            ]
        })

    def post(self, request):
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color       = request.POST.get('color', '#6366f1').strip()
        icon        = request.POST.get('icon', 'people-fill').strip()
        is_global   = 'is_global' in request.POST

        if not name:
            return render(request, 'teams/create.html', {
                'error': 'Team name is required.',
                'post':  request.POST,
                'color_presets': [
                    '#6366f1', '#2d6a4f', '#e07c24', '#2980b9',
                    '#8e44ad', '#c0392b', '#16a085', '#d35400',
                ]
            })

        slug = slugify(name)

        # Ensure unique slug
        base_slug, counter = slug, 1
        while Team.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        team = Team.objects.create(
            name=name, slug=slug,
            description=description,
            color=color, icon=icon,
            is_global=is_global,
        )

        # Auto-add creator as team lead
        TeamMembership.objects.create(
            team=team, user=request.user, role='lead'
        )

        return redirect('teams:team-detail', slug=team.slug)


class TeamUserListView(StaffRequiredMixin, ListView):
    """
    Staff-only view: all users with their current team memberships.
    Allows assigning users to teams inline via HTMX.
    """
    template_name    = 'teams/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        qs = User.objects.filter(is_active=True).prefetch_related(
            'team_memberships__team'
        ).order_by('display_name', 'username')

        if q := self.request.GET.get('q', '').strip():
            qs = qs.filter(
                models.Q(display_name__icontains=q) |
                models.Q(email__icontains=q) |
                models.Q(username__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_teams'] = Team.objects.filter(is_active=True).order_by('name')
        ctx['q']         = self.request.GET.get('q', '')
        return ctx


class TeamUserAssignView(StaffRequiredMixin, View):
    """
    HTMX — assign a user to a team with a role.
    Returns updated team membership row for that user.
    """
    def post(self, request, user_pk):
        user    = get_object_or_404(User, pk=user_pk)
        team_id = request.POST.get('team_id')
        role    = request.POST.get('role', 'member')

        if not team_id:
            return HttpResponseBadRequest('team_id is required.')

        team = get_object_or_404(Team, pk=team_id)
        TeamMembership.objects.get_or_create(
            user=user, team=team,
            defaults={'role': role}
        )

        return render(request, 'teams/partials/user_team_badges.html', {
            'u': user,
            'memberships': user.team_memberships.select_related('team').all(),
            'all_teams':   Team.objects.filter(is_active=True).order_by('name'),
        })


class TeamUserRemoveView(StaffRequiredMixin, View):
    """
    HTMX — remove a user from a specific team.
    Returns updated team membership badges for that user.
    """
    def post(self, request, user_pk, slug):
        team = get_object_or_404(Team, slug=slug)
        TeamMembership.objects.filter(user_id=user_pk, team=team).delete()

        user = get_object_or_404(User, pk=user_pk)
        return render(request, 'teams/partials/user_team_badges.html', {
            'u':           user,
            'memberships': user.team_memberships.select_related('team').all(),
            'all_teams':   Team.objects.filter(is_active=True).order_by('name'),
        })


class TeamProjectAddView(LoginRequiredMixin, View):
    """
    HTMX — assign this team to a project.
    Only leads and staff can do this.
    Returns updated project list partial.
    """
    def dispatch(self, request, *args, **kwargs):
        self.team   = get_object_or_404(Team, slug=kwargs['slug'])
        is_lead     = self.team.memberships.filter(user=request.user, role='lead').exists()
        if not (is_lead or request.user.is_staff):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, slug):
        from apps.projects.models import Project, ProjectTeamMembership
        project_id = request.POST.get('project_id')
        role       = request.POST.get('role', 'contributor')
        project    = get_object_or_404(Project, pk=project_id)

        ProjectTeamMembership.objects.get_or_create(
            project=project,
            team=self.team,
            defaults={'role': role}
        )

        return render(request, 'teams/partials/project_list.html',
                      self._ctx())

    def _ctx(self):
        from apps.projects.models import Project
        return {
            'team':               self.team,
            'projects':           self.team.member_projects.exclude(status='archived').order_by('-updated_at'),
            'available_projects': Project.objects.exclude(status='archived').exclude(
                                      team_members=self.team
                                  ).order_by('name'),
            'is_lead':            self.team.memberships.filter(user=self.request.user, role='lead').exists(),
        }


class TeamProjectRemoveView(LoginRequiredMixin, View):
    """
    HTMX — remove this team from a project.
    Only leads and staff can do this.
    Returns updated project list partial.
    """
    def dispatch(self, request, *args, **kwargs):
        self.team = get_object_or_404(Team, slug=kwargs['slug'])
        is_lead   = self.team.memberships.filter(user=request.user, role='lead').exists()
        if not (is_lead or request.user.is_staff):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, slug, project_pk):
        from apps.projects.models import ProjectTeamMembership, Project
        ProjectTeamMembership.objects.filter(
            team=self.team, project_id=project_pk
        ).delete()

        return render(request, 'teams/partials/project_list.html', {
            'team':               self.team,
            'projects':           self.team.member_projects.exclude(status='archived').order_by('-updated_at'),
            'available_projects': Project.objects.exclude(status='archived').exclude(
                                      team_members=self.team
                                  ).order_by('name'),
            'is_lead':            self.team.memberships.filter(user=self.request.user, role='lead').exists(),
        })
