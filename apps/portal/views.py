"""Portal views for customer portal."""
from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.portal.mixins import PortalUserRequiredMixin
from apps.tasks.models import Attachment, Comment, Task, TaskTemplate


class PortalHomeView(PortalUserRequiredMixin, TemplateView):
    """Portal home page with overview."""
    template_name = 'portal/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['client'] = user.portal_client
        ctx['open_count'] = Task.objects.filter(
            requester=user).exclude(status='done').count()
        ctx['done_count'] = Task.objects.filter(
            requester=user, status='done').count()
        ctx['recent_tickets'] = Task.objects.filter(
            requester=user
        ).select_related('project').order_by('-created_at')[:5]
        return ctx


class PortalTemplateSelectView(PortalUserRequiredMixin, TemplateView):
    """Template selection page for creating tickets."""
    template_name = 'portal/template_select.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = self.request.user.portal_client

        templates = TaskTemplate.objects.filter(
            is_active=True,
            is_portal_visible=True,
        ).filter(
            models.Q(client__isnull=True) |
            models.Q(client=client)
        ).order_by('client', 'name')

        ctx['global_templates'] = templates.filter(client__isnull=True)
        ctx['client_templates'] = templates.filter(client=client)
        ctx['has_templates'] = templates.exists()
        return ctx


class PortalTicketCreateView(PortalUserRequiredMixin, View):
    """Create a ticket from a template."""

    def _get_template(self, request, template_slug):
        client = request.user.portal_client
        template = get_object_or_404(
            TaskTemplate, slug=template_slug,
            is_active=True, is_portal_visible=True,
        )
        if template.client and template.client != client:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return template

    def get(self, request, template_slug):
        template = self._get_template(request, template_slug)
        extra_fields = template.get_extra_fields()
        return render(request, 'portal/ticket_create.html', {
            'template': template,
            'extra_fields': extra_fields,
            'priority_choices': [
                (1, 'Niedrig'),
                (2, 'Mittel'),
                (3, 'Hoch'),
                (4, 'Kritisch')
            ],
        })

    def post(self, request, template_slug):
        template = self._get_template(request, template_slug)
        extra_fields = template.get_extra_fields()
        client = request.user.portal_client

        from apps.tasks.template_utils import (
            validate_extra_fields,
            render_extra_fields_to_description,
        )

        errors = validate_extra_fields(extra_fields, request.POST)
        title = request.POST.get('title', '').strip()
        if not title:
            errors.insert(0, 'Titel ist ein Pflichtfeld.')

        if errors:
            return render(request, 'portal/ticket_create.html', {
                'template': template,
                'extra_fields': extra_fields,
                'errors': errors,
                'post': request.POST,
                'priority_choices': [
                    (1, 'Niedrig'),
                    (2, 'Mittel'),
                    (3, 'Hoch'),
                    (4, 'Kritisch')
                ],
            })

        extra_desc = render_extra_fields_to_description(extra_fields, request.POST)
        manual_desc = request.POST.get('description', '').strip()
        full_desc = f'{extra_desc}\n\n---\n\n{manual_desc}' \
                    if extra_desc and manual_desc \
                    else extra_desc or manual_desc

        if not template.default_project:
            return render(request, 'portal/ticket_create.html', {
                'template': template,
                'extra_fields': extra_fields,
                'errors': ['Diese Vorlage hat kein Standard-Projekt. '
                           'Bitte kontaktiere den Support.'],
            })

        task = Task.objects.create(
            title=title,
            description=full_desc,
            project=template.default_project,
            assigned_to_team=template.default_assigned_to_team,
            priority=request.POST.get('priority', template.default_priority),
            due_date=request.POST.get('due_date') or None,
            status=Task.STATUS_BACKLOG,
            created_by=request.user,
            requester=request.user,
            client=client,
            template=template,
        )

        for file in request.FILES.getlist('attachments'):
            Attachment.objects.create(
                task=task, uploaded_by=request.user,
                file=file, filename=file.name, size_bytes=file.size,
            )

        from apps.mail.dispatcher import dispatch
        from apps.mail.models import MailHook
        dispatch(
            event=MailHook.EVENT_PORTAL_CREATED,
            context={
                'recipient_name': request.user.full_name,
                'task_title': task.title,
                'task_url': f'{settings.SITE_URL}/portal/tickets/{task.pk}/',
                'template_name': template.name,
                'client_name': client.name if client else '',
            },
            task=task,
        )

        return redirect('portal-ticket-detail', pk=task.pk)


class PortalTicketListView(PortalUserRequiredMixin, ListView):
    """List all tickets for the portal user."""
    template_name = 'portal/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 20

    def get_queryset(self):
        qs = Task.objects.filter(
            requester=self.request.user
        ).select_related('project').order_by('-created_at')
        if status := self.request.GET.get('status'):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['status_choices'] = Task.STATUS_CHOICES
        ctx['open_count'] = Task.objects.filter(
            requester=self.request.user
        ).exclude(status='done').count()
        return ctx


class PortalTicketDetailView(PortalUserRequiredMixin, DetailView):
    """Detail view for a single ticket."""
    template_name = 'portal/ticket_detail.html'

    def get_queryset(self):
        return Task.objects.filter(
            requester=self.request.user
        ).prefetch_related('comments__author', 'attachments__uploaded_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        portal_status = {
            'backlog': ('Eingegangen', 'secondary'),
            'todo': ('Zu erledigen', 'primary'),
            'in_progress': ('In Bearbeitung', 'warning'),
            'review': ('In Prüfung', 'info'),
            'done': ('Erledigt', 'success'),
        }
        label, color = portal_status.get(self.object.status, ('Unbekannt', 'secondary'))
        ctx['status_label'] = label
        ctx['status_color'] = color
        return ctx


class PortalTicketCommentView(PortalUserRequiredMixin, View):
    """Add a comment to a ticket via HTMX."""

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, requester=request.user)
        body = request.POST.get('body', '').strip()
        if body:
            Comment.objects.create(task=task, author=request.user, body=body)
        comments = task.comments.select_related('author').order_by('created_at')
        return render(request, 'portal/partials/comment_list.html',
                      {'task': task, 'comments': comments})


class PortalTicketAttachmentView(PortalUserRequiredMixin, View):
    """Upload an attachment to a ticket via HTMX."""

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, requester=request.user)
        file = request.FILES.get('file')
        if file:
            Attachment.objects.create(
                task=task, uploaded_by=request.user,
                file=file, filename=file.name, size_bytes=file.size,
            )
        attachments = task.attachments.select_related('uploaded_by').order_by('created_at')
        return render(request, 'portal/partials/attachment_list.html',
                      {'task': task, 'attachments': attachments})
