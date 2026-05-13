"""
Core views for error handling and shared functionality.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView

from .models import Client, CapacityBudget
from apps.teams.models import Team


class StaffRequiredMixin(LoginRequiredMixin):
    """Restrict view to staff users only."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def handler404(request, exception):
    """Custom 404 error handler."""
    return render(request, '404.html', status=404)


def handler500(request):
    """Custom 500 error handler."""
    return render(request, '500.html', status=500)


class ClientListView(LoginRequiredMixin, ListView):
    """All clients — visible to all authenticated users (read), edit for staff."""
    model = Client
    template_name = 'clients/list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        return Client.objects.filter(is_active=True).annotate(
            project_count=Count('projects', distinct=True),
            open_task_count=Count('tasks',
                filter=~models.Q(tasks__status='done'), distinct=True),
        )


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/detail.html'

    def get_context_data(self, **kwargs):
        from apps.tasks.models import Task
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = self.object.projects.exclude(
            status='archived'
        ).order_by('-updated_at')
        ctx['open_tasks'] = Task.objects.filter(
            models.Q(client=self.object) |
            models.Q(project__client=self.object)
        ).exclude(status='done').select_related(
            'project', 'assigned_to_user', 'assigned_to_team'
        ).order_by('due_date', '-priority')[:20]
        return ctx


class ClientCreateView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'clients/form.html')

    def post(self, request):
        name       = request.POST.get('name', '').strip()
        short_name = request.POST.get('short_name', '').strip()
        color      = request.POST.get('color', '#6366f1')
        description= request.POST.get('description', '').strip()
        website    = request.POST.get('website', '').strip()

        if not name:
            return render(request, 'clients/form.html',
                          {'error': 'Name is required.'})

        slug = slugify(name)
        base, n = slug, 1
        while Client.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'; n += 1

        client = Client.objects.create(
            name=name, slug=slug, short_name=short_name,
            color=color, description=description, website=website,
        )
        return redirect('core:client-detail', slug=client.slug)


class ClientEditView(StaffRequiredMixin, UpdateView):
    model = Client
    template_name = 'clients/form.html'
    fields = ['name', 'short_name', 'description', 'color', 'website', 'is_active']

    def get_success_url(self):
        return reverse('core:client-detail', kwargs={'slug': self.object.slug})


class BudgetListView(StaffRequiredMixin, View):
    """
    HTMX — gibt die aktuelle Budget-Tabelle zurück.
    Wird nach Add/Edit/Delete aufgerufen um die Tabelle zu aktualisieren.
    """
    def get(self, request, slug):
        client = get_object_or_404(Client, slug=slug)
        budgets = CapacityBudget.objects.filter(
            client=client
        ).select_related('team').order_by('team__name', '-valid_from')

        teams_without_budget = Team.objects.filter(
            is_active=True
        ).exclude(
            capacity_budgets__client=client,
            capacity_budgets__valid_until__isnull=True,
        ).order_by('name')

        return render(request, 'clients/partials/budget_table.html', {
            'client':               client,
            'budgets':              budgets,
            'teams_without_budget': teams_without_budget,
            'all_teams':            Team.objects.filter(is_active=True).order_by('name'),
        })


class BudgetAddView(StaffRequiredMixin, View):
    """
    HTMX — neues Budget hinzufügen.
    POST: team_id, weekly_sp_budget, valid_from, valid_until (optional), notes
    Gibt aktualisierte Budget-Tabelle zurück.
    """
    def post(self, request, slug):
        client      = get_object_or_404(Client, slug=slug)
        team_id     = request.POST.get('team_id')
        sp_budget   = request.POST.get('weekly_sp_budget', '').strip()
        valid_from  = request.POST.get('valid_from', '').strip()
        valid_until = request.POST.get('valid_until', '').strip() or None
        notes       = request.POST.get('notes', '').strip()

        errors = []
        if not team_id:
            errors.append('Team ist erforderlich.')
        if not sp_budget:
            errors.append('Story Points pro Woche ist erforderlich.')
        if not valid_from:
            errors.append('Gültig ab ist erforderlich.')

        if errors:
            return render(request, 'clients/partials/budget_form.html', {
                'client': client,
                'errors': errors,
                'post':   request.POST,
                'all_teams': Team.objects.filter(is_active=True).order_by('name'),
            })

        CapacityBudget.objects.create(
            client          = client,
            team_id         = team_id,
            weekly_sp_budget= sp_budget,
            valid_from      = valid_from,
            valid_until     = valid_until or None,
            notes           = notes,
            created_by      = request.user,
        )

        # Tabelle neu rendern
        return self._budget_table(request, client)

    def _budget_table(self, request, client):
        budgets = CapacityBudget.objects.filter(
            client=client
        ).select_related('team').order_by('team__name', '-valid_from')
        return render(request, 'clients/partials/budget_table.html', {
            'client':    client,
            'budgets':   budgets,
            'all_teams': Team.objects.filter(is_active=True).order_by('name'),
        })


class BudgetEditView(StaffRequiredMixin, View):
    """
    GET  → gibt Edit-Formular für ein Budget zurück (HTMX inline)
    POST → speichert Änderungen, gibt aktualisierte Tabelle zurück
    """
    def get(self, request, slug, pk):
        client = get_object_or_404(Client, slug=slug)
        budget = get_object_or_404(CapacityBudget, pk=pk, client=client)
        return render(request, 'clients/partials/budget_edit_row.html', {
            'client': client,
            'budget': budget,
            'all_teams': Team.objects.filter(is_active=True).order_by('name'),
        })

    def post(self, request, slug, pk):
        client = get_object_or_404(Client, slug=slug)
        budget = get_object_or_404(CapacityBudget, pk=pk, client=client)

        budget.team_id          = request.POST.get('team_id', budget.team_id)
        budget.weekly_sp_budget = request.POST.get('weekly_sp_budget', budget.weekly_sp_budget)
        budget.valid_from       = request.POST.get('valid_from', budget.valid_from)
        budget.valid_until      = request.POST.get('valid_until') or None
        budget.notes            = request.POST.get('notes', budget.notes)
        budget.save()

        budgets = CapacityBudget.objects.filter(
            client=client
        ).select_related('team').order_by('team__name', '-valid_from')
        return render(request, 'clients/partials/budget_table.html', {
            'client':    client,
            'budgets':   budgets,
            'all_teams': Team.objects.filter(is_active=True).order_by('name'),
        })


class BudgetDeleteView(StaffRequiredMixin, View):
    """HTMX — Budget löschen, gibt aktualisierte Tabelle zurück."""
    def post(self, request, slug, pk):
        client = get_object_or_404(Client, slug=slug)
        budget = get_object_or_404(CapacityBudget, pk=pk, client=client)
        budget.delete()

        budgets = CapacityBudget.objects.filter(
            client=client
        ).select_related('team').order_by('team__name', '-valid_from')
        return render(request, 'clients/partials/budget_table.html', {
            'client':    client,
            'budgets':   budgets,
            'all_teams': Team.objects.filter(is_active=True).order_by('name'),
        })

