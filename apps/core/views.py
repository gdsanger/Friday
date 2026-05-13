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

from .models import Client


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

