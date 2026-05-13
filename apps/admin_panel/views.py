"""
Admin panel views for Friday project.
"""
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView

from apps.projects.models import Project
from apps.tasks.models import Task
from apps.teams.models import Team, TeamMembership
from apps.ai.models import AIGlobalSettings, AIProviderConfig, AIUsageLog
from apps.mail.models import WebhookSubscription, MailThread
from apps.core.models import Organisation
from .mixins import StaffRequiredMixin

User = get_user_model()


class AdminDashboardView(StaffRequiredMixin, TemplateView):
    """Admin dashboard home page showing key stats."""
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user_count']    = User.objects.filter(is_active=True).count()
        ctx['team_count']    = Team.objects.filter(is_active=True).count()
        ctx['project_count'] = Project.objects.exclude(status='archived').count()
        ctx['task_count']    = Task.objects.exclude(status='done').count()

        # AI usage today
        today = timezone.now().date()
        ctx['ai_tokens_today'] = AIUsageLog.objects.filter(
            created_at__date=today
        ).aggregate(t=Sum('total_tokens'))['t'] or 0

        ctx['ai_enabled']    = AIGlobalSettings.get().is_enabled
        ctx['recent_errors'] = AIUsageLog.objects.filter(
            success=False
        ).order_by('-created_at')[:5]
        return ctx


class AdminUserListView(StaffRequiredMixin, ListView):
    """List all users with search and filters."""
    template_name = 'admin_panel/users/list.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.prefetch_related('team_memberships__team').order_by('display_name', 'username')
        if q := self.request.GET.get('q'):
            qs = qs.filter(
                models.Q(display_name__icontains=q) |
                models.Q(email__icontains=q) |
                models.Q(username__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_teams'] = Team.objects.filter(is_active=True).order_by('name')
        return ctx


class AdminUserDetailView(StaffRequiredMixin, View):
    """View and edit user details."""
    template_name = 'admin_panel/users/detail.html'

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        from apps.core.models import Client
        return render(request, self.template_name, {
            'user_obj': user,
            'teams': user.teams,
            'projects': Project.objects.filter(
                Q(user_members=user) | Q(team_members__in=user.teams)
            ).distinct()[:10],
            'created_tasks': user.created_tasks.all()[:10],
            'assigned_tasks': user.assigned_tasks.all()[:10],
            'clients': Client.objects.filter(is_active=True).order_by('name'),
        })


class AdminUserInviteView(StaffRequiredMixin, View):
    """Create a new user account and send invitation email."""
    def post(self, request):
        email        = request.POST.get('email', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        team_id      = request.POST.get('team_id')

        if not email:
            messages.error(request, 'Email is required.')
            return redirect('admin_panel:admin-users')

        username = email.split('@')[0]
        # Check if user already exists
        if User.objects.filter(Q(email=email) | Q(username=username)).exists():
            messages.error(request, 'User with this email or username already exists.')
            return redirect('admin_panel:admin-users')

        user = User.objects.create_user(
            username=username,
            email=email,
            display_name=display_name,
        )
        user.set_unusable_password()
        user.save()

        if team_id:
            TeamMembership.objects.get_or_create(
                user=user, team_id=team_id, defaults={'role': 'member'}
            )

        # Send invitation email (Celery task)
        try:
            from apps.accounts.tasks import send_invitation_email
            send_invitation_email.delay(user.pk)
            messages.success(request, f'User {email} invited successfully.')
        except Exception as e:
            messages.warning(request, f'User created but invitation email failed: {e}')

        if request.htmx:
            users = User.objects.prefetch_related('team_memberships__team').order_by('display_name')
            return render(request, 'admin_panel/users/partials/user_table.html',
                          {'users': users})
        return redirect('admin_panel:admin-users')


class AdminUserToggleActiveView(StaffRequiredMixin, View):
    """HTMX — toggle user active status, return updated row."""
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user != request.user:  # can't deactivate yourself
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
        return render(request, 'admin_panel/users/partials/user_row.html', {'u': user})


class AdminTeamListView(StaffRequiredMixin, ListView):
    """List all teams."""
    template_name = 'admin_panel/teams/list.html'
    context_object_name = 'teams'
    paginate_by = 30

    def get_queryset(self):
        return Team.objects.annotate(
            member_count=Count('memberships'),
            project_count=Count('member_projects', distinct=True),
        ).order_by('name')


class AdminTeamCreateView(StaffRequiredMixin, View):
    """Create a new team."""
    def post(self, request):
        from django.utils.text import slugify
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#6366f1')

        if not name:
            messages.error(request, 'Team name is required.')
            return redirect('admin_panel:admin-teams')

        slug = slugify(name)
        if Team.objects.filter(slug=slug).exists():
            messages.error(request, 'Team with this name already exists.')
            return redirect('admin_panel:admin-teams')

        team = Team.objects.create(
            name=name,
            slug=slug,
            description=description,
            color=color,
        )
        messages.success(request, f'Team "{name}" created successfully.')
        return redirect('admin_panel:admin-teams')


class AdminTeamEditView(StaffRequiredMixin, View):
    """Edit team details."""
    template_name = 'admin_panel/teams/edit.html'

    def get(self, request, slug):
        team = get_object_or_404(Team, slug=slug)
        return render(request, self.template_name, {'team': team})

    def post(self, request, slug):
        team = get_object_or_404(Team, slug=slug)
        team.name = request.POST.get('name', team.name)
        team.description = request.POST.get('description', team.description)
        team.color = request.POST.get('color', team.color)
        team.icon = request.POST.get('icon', team.icon)
        team.is_active = 'is_active' in request.POST
        team.save()
        messages.success(request, f'Team "{team.name}" updated successfully.')
        return redirect('admin_panel:admin-teams')


class AdminAIMonitorView(StaffRequiredMixin, View):
    """AI usage monitoring and stats."""
    template_name = 'admin_panel/ai/monitor.html'

    def get(self, request):
        today   = timezone.now().date()
        month_start = today.replace(day=1)

        # Token usage aggregates
        ctx = {
            'tokens_today':   self._tokens_since(today),
            'tokens_month':   self._tokens_since(month_start),
            'top_users':      AIUsageLog.objects.values(
                                  'user__display_name', 'user__username'
                              ).annotate(t=Sum('total_tokens')).order_by('-t')[:10],
            'top_teams':      AIUsageLog.objects.values(
                                  'team__name'
                              ).annotate(t=Sum('total_tokens')).order_by('-t')[:10],
            'by_provider':    AIUsageLog.objects.values(
                                  'provider'
                              ).annotate(t=Sum('total_tokens'), calls=Count('id')),
            'daily_trend':    self._daily_trend(days=30),
            'recent_errors':  AIUsageLog.objects.filter(
                                  success=False
                              ).select_related('user').order_by('-created_at')[:20],
            'settings':       AIGlobalSettings.get(),
            'providers':      AIProviderConfig.objects.all(),
        }
        return render(request, self.template_name, ctx)

    def _tokens_since(self, date):
        return AIUsageLog.objects.filter(
            created_at__date__gte=date
        ).aggregate(t=Sum('total_tokens'))['t'] or 0

    def _daily_trend(self, days=30):
        cutoff = timezone.now() - timedelta(days=days)
        return AIUsageLog.objects.filter(
            created_at__gte=cutoff
        ).annotate(day=TruncDate('created_at')).values('day').annotate(
            t=Sum('total_tokens')
        ).order_by('day')


class AdminAISettingsView(StaffRequiredMixin, View):
    """Update AIGlobalSettings and AIProviderConfig."""
    def post(self, request):
        settings_obj = AIGlobalSettings.get()
        settings_obj.default_provider     = request.POST.get('default_provider', 'openai')
        settings_obj.fallback_provider    = request.POST.get('fallback_provider', '')
        settings_obj.per_user_daily_limit = int(request.POST.get('per_user_daily_limit', 50000))
        settings_obj.is_enabled           = 'is_enabled' in request.POST
        settings_obj.save()

        # Update provider API keys if provided (non-empty)
        for provider in ['openai', 'claude']:
            api_key    = request.POST.get(f'{provider}_api_key', '').strip()
            model_name = request.POST.get(f'{provider}_model', '').strip()
            if api_key or model_name:
                config, _ = AIProviderConfig.objects.get_or_create(provider=provider)
                if api_key:
                    config.api_key = api_key
                if model_name:
                    config.model_name = model_name
                config.save()

        messages.success(request, 'AI settings updated.')
        return redirect('admin_panel:admin-ai')


class AdminMailStatusView(StaffRequiredMixin, TemplateView):
    """Mail service status and webhook subscriptions."""
    template_name = 'admin_panel/mail/status.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subscriptions'] = WebhookSubscription.objects.select_related('user').order_by('expiration')
        ctx['recent_threads'] = MailThread.objects.select_related(
            'task', 'task__project'
        ).order_by('-created_at')[:20]
        return ctx


class AdminOrgSettingsView(StaffRequiredMixin, View):
    """Organisation settings management."""
    template_name = 'admin_panel/settings.html'

    def get(self, request):
        org = Organisation.get()
        return render(request, self.template_name, {'org': org})

    def post(self, request):
        org = Organisation.get()
        org.name        = request.POST.get('name', org.name)
        org.description = request.POST.get('description', org.description)
        org.website     = request.POST.get('website', org.website)
        if logo := request.FILES.get('logo'):
            org.logo = logo
        org.save()
        messages.success(request, 'Organisation settings saved.')
        return redirect('admin_panel:admin-settings')


class AdminAuditLogView(StaffRequiredMixin, TemplateView):
    """Audit log view (placeholder)."""
    template_name = 'admin_panel/audit.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Placeholder - in future, this would show audit logs
        ctx['logs'] = []
        return ctx


class AdminUserPortalSettingsView(StaffRequiredMixin, View):
    """Update portal settings for a user."""
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_portal_user = 'is_portal_user' in request.POST
        user.portal_client_id = request.POST.get('portal_client') or None
        user.save(update_fields=['is_portal_user', 'portal_client'])
        messages.success(request, f'Portal settings updated for {user.full_name}.')
        return redirect('admin_panel:admin-user-detail', pk=pk)
