"""
Team views for Friday project.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.text import slugify
from django.views import View
from django.views.generic import ListView, DetailView

from .models import Team, TeamMembership

User = get_user_model()


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
        ctx['projects'] = self.object.member_projects.filter(
            status__in=['planning', 'active', 'on_hold']
        ).order_by('-updated_at')[:10]
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
