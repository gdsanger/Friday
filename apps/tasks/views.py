"""
Task views for Friday project.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from .models import Task, Comment, Attachment, TimeEntry

User = get_user_model()


class TaskDetailView(LoginRequiredMixin, View):
    """
    Returns full slide-over panel HTML (HTMX target: #slide-over).
    Also handles direct URL access (hx-push-url=true).
    """
    def get(self, request, pk):
        task = get_object_or_404(
            Task.objects.select_related(
                'project', 'created_by',
                'assigned_to_user', 'assigned_to_team',
                'parent_task',
            ).prefetch_related(
                'subtasks', 'labels', 'comments__author',
                'attachments', 'time_entries__user',
                'watching_users', 'watching_teams',
            ),
            pk=pk
        )
        if not task.project.is_member(request.user):
            raise PermissionDenied

        # Import Team model for global teams query
        from apps.teams.models import Team
        from apps.core.models import Client

        ctx = {
            'task': task,
            'project_members': task.project.get_all_members(),
            'project_teams':   Team.objects.filter(
                models.Q(projectteammembership__project=task.project) |
                models.Q(is_global=True),
                is_active=True
            ).distinct().order_by('name'),
            'is_watching':     request.user in task.get_all_watchers(),
            'total_time_m':    task.time_entries.aggregate(
                                   t=Sum('duration_m'))['t'] or 0,
            'user_role':       task.project.get_effective_role(request.user),
            'clients':         Client.objects.filter(is_active=True).order_by('name'),
            'project_tasks':   task.project.tasks.exclude(pk=task.pk).order_by('title'),
        }
        template = 'tasks/partials/slide_over.html' if request.htmx else 'tasks/detail.html'
        return render(request, template, ctx)


class TaskCreateView(LoginRequiredMixin, View):
    """
    Full task creation form and HTMX inline quick-create.
    GET: Returns task creation form page.
    POST: Creates task and returns card partial (HTMX) or redirects (full form).
    """
    def get(self, request):
        """
        Full task creation form page.
        Optional: ?project=<id> or ?project_id=<id> pre-selects the project.
        Optional: ?status=<status> pre-selects the status column.
        Optional: ?slide_over=1 returns slide-over template for HTMX.
        """
        from apps.projects.models import Project
        from apps.core.models import Client

        project_id = request.GET.get('project_id') or request.GET.get('project')
        status     = request.GET.get('status', Task.STATUS_BACKLOG)
        slide_over = request.GET.get('slide_over')

        # Only show projects the user is a member of (including via global teams)
        accessible_projects = Project.objects.filter(
            models.Q(user_members=request.user) |
            models.Q(team_members__in=request.user.teams) |
            models.Q(visibility='organisation')  # Org-visible projects are also accessible
        ).distinct().order_by('name')

        selected_project = None
        if project_id:
            selected_project = accessible_projects.filter(pk=project_id).first()

        ctx = {
            'accessible_projects': accessible_projects,
            'selected_project':    selected_project,
            'selected_status':     status,
            'status_choices':      Task.STATUS_CHOICES,
            'priority_choices':    Task.PRIORITY_CHOICES,
            'teams':               request.user.teams,
            'clients':             Client.objects.filter(is_active=True).order_by('name'),
        }

        # Return slide-over form for HTMX with slide_over parameter
        if request.htmx and slide_over:
            return render(request, 'tasks/partials/create_slide_over.html', ctx)
        # Return quick-add form for HTMX without slide_over parameter
        elif request.htmx:
            return render(request, 'tasks/partials/quick_add_form.html', ctx)
        # Return full page form for regular requests
        return render(request, 'tasks/create.html', ctx)

    def post(self, request):
        """
        Handles:
        - Full page form submission (non-HTMX) → redirect to task detail
        - HTMX quick-add from Kanban column → return card partial
        - HTMX slide-over form → redirect to task detail in slide-over
        """
        from apps.projects.models import Project

        project_id = request.POST.get('project_id') or request.POST.get('project')
        if not project_id:
            return HttpResponseBadRequest('project_id is required')

        project = get_object_or_404(Project, pk=project_id)
        if not project.is_member(request.user):
            raise PermissionDenied

        title = request.POST.get('title', '').strip()
        if not title:
            if request.htmx:
                return HttpResponseBadRequest('Title is required')
            return render(request, 'tasks/create.html', {
                'error': 'Title is required',
                'accessible_projects': Project.objects.filter(
                    models.Q(user_members=request.user) |
                    models.Q(team_members__in=request.user.teams)
                ).distinct(),
                'status_choices':      Task.STATUS_CHOICES,
                'priority_choices':    Task.PRIORITY_CHOICES,
                'teams':               request.user.teams,
            })

        task = Task.objects.create(
            title       = title,
            description = request.POST.get('description', ''),
            project     = project,
            status      = request.POST.get('status', Task.STATUS_BACKLOG),
            priority    = int(request.POST.get('priority', Task.PRIORITY_NONE)),
            created_by  = request.user,
            due_date    = request.POST.get('due_date') or None,
            deadline    = request.POST.get('deadline') or None,
            client_id   = request.POST.get('client') or None,
            story_points = request.POST.get('story_points') or None,
        )

        # Optional: set requester
        requester_id = request.POST.get('requester')
        if requester_id:
            task.requester_id = requester_id
            task.save(update_fields=['requester'])

        # Optional: assign immediately
        user_id = request.POST.get('assigned_to_user')
        team_id = request.POST.get('assigned_to_team')
        if user_id:
            task.assigned_to_user_id = user_id
            task.save(update_fields=['assigned_to_user'])
        elif team_id:
            task.assigned_to_team_id = team_id
            task.save(update_fields=['assigned_to_team'])

        # HTMX requests
        if request.htmx:
            # Check if this is a slide-over submission by checking the target
            # Slide-over submissions target #slide-over, quick-add targets .kanban-cards
            hx_target = request.headers.get('HX-Target', '')
            if hx_target == 'slide-over':
                # Redirect to task detail in slide-over
                from django.http import HttpResponse
                response = HttpResponse()
                response['HX-Redirect'] = f'/tasks/{task.pk}/detail/'
                return response
            else:
                # Quick-add from Kanban column → return card partial
                return render(request, 'tasks/partials/card.html', {'task': task})

        # Full page form → redirect to task detail
        return redirect('tasks:task-detail', pk=task.pk)


class TaskEditView(LoginRequiredMixin, View):
    """HTMX — update task fields. Returns updated field partial."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        # Update fields based on what's provided
        if 'title' in request.POST:
            task.title = request.POST['title'].strip()
        if 'description' in request.POST:
            task.description = request.POST['description'].strip()
        if 'priority' in request.POST:
            task.priority = int(request.POST['priority'])
        if 'due_date' in request.POST:
            due_date = request.POST['due_date'].strip()
            task.due_date = due_date if due_date else None
        if 'deadline' in request.POST:
            deadline = request.POST['deadline'].strip()
            task.deadline = deadline if deadline else None
        if 'client' in request.POST:
            client_id = request.POST['client'].strip()
            task.client_id = client_id if client_id else None
        if 'story_points' in request.POST:
            story_points = request.POST['story_points'].strip()
            task.story_points = story_points if story_points else None

        task.save()
        return HttpResponse(status=204)


class TaskDeleteView(LoginRequiredMixin, View):
    """Delete task. Returns 204 No Content."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        # Only creator or project managers can delete
        role = task.project.get_effective_role(request.user)
        if task.created_by != request.user and role != 'manager':
            raise PermissionDenied
        task.delete()
        return HttpResponse(status=204)


class TaskStatusView(LoginRequiredMixin, View):
    """HTMX — update status (used by Kanban drag-drop and detail panel)."""
    def post(self, request, pk):
        task     = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        status   = request.POST.get('status')
        position = request.POST.get('position')

        # Block transition to in_progress if task is blocked
        if status == Task.STATUS_IN_PROGRESS and task.is_blocked:
            blocking = task.blocking_tasks.exclude(status=Task.STATUS_DONE)
            return render(request, 'tasks/partials/blocked_warning.html', {
                'task':     task,
                'blocking': blocking,
            }, status=409)

        if status in dict(Task.STATUS_CHOICES):
            task.status = status
        if position is not None:
            task.position = int(position)
        task.save(update_fields=['status', 'position'])
        return HttpResponse(status=204)


class TaskAssignView(LoginRequiredMixin, View):
    """HTMX — assign to user OR team (mutually exclusive). Returns assignee partial."""
    def post(self, request, pk):
        from django.conf import settings
        from apps.teams.models import Team
        from apps.mail.dispatcher import dispatch
        from apps.mail.models import MailHook

        task      = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        user_id   = request.POST.get('user_id')
        team_id   = request.POST.get('team_id')

        # Store old assignments for comparison
        old_user = task.assigned_to_user
        old_team = task.assigned_to_team

        # XOR enforcement: User gewählt → Team leeren, Team gewählt → User leeren
        if user_id:
            task.assigned_to_user = User.objects.get(pk=user_id)
            task.assigned_to_team = None
        elif team_id:
            task.assigned_to_team = Team.objects.get(pk=team_id)
            task.assigned_to_user = None
        else:
            # Beide leer → Zuweisung aufheben
            task.assigned_to_user = None
            task.assigned_to_team = None

        task.save(update_fields=['assigned_to_user', 'assigned_to_team'])

        # Send mail if new assignee is set
        context = {
            'task_title':   task.title,
            'task_url':     f'{settings.SITE_URL}/tasks/{task.pk}/',
            'project_name': task.project.name,
            'assigned_by':  request.user.full_name,
            'due_date':     task.due_date.strftime('%d.%m.%Y') if task.due_date else '',
            'priority':     task.get_priority_display(),
        }

        if task.assigned_to_user and task.assigned_to_user != request.user:
            # Mail to newly assigned user
            dispatch(
                event=MailHook.EVENT_TASK_ASSIGNED,
                context={
                    **context,
                    'recipient_name': task.assigned_to_user.full_name,
                },
                recipients_override=[task.assigned_to_user.email],
            )

        elif task.assigned_to_team:
            # Mail to all team members
            dispatch(
                event=MailHook.EVENT_TASK_ASSIGNED,
                context={
                    **context,
                    'recipient_name': f'Team {task.assigned_to_team.name}',
                },
                task=task,
            )

        # Close modal signal
        response = render(request, 'tasks/partials/assignee.html', {'task': task})
        response['HX-Trigger'] = 'taskAssigned'
        return response


class TaskWatchView(LoginRequiredMixin, View):
    """HTMX — toggle current user as watcher. Returns watcher button partial."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        if request.user in task.watching_users.all():
            task.watching_users.remove(request.user)
            watching = False
        else:
            task.watching_users.add(request.user)
            watching = True
        return render(request, 'tasks/partials/watch_button.html',
                      {'task': task, 'is_watching': watching})


class TaskCommentView(LoginRequiredMixin, View):
    """HTMX — add comment, returns updated comment list partial."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        body = request.POST.get('body', '').strip()
        if body:
            Comment.objects.create(task=task, author=request.user, body=body)
        comments = task.comments.select_related('author').order_by('created_at')
        return render(request, 'tasks/partials/comment_list.html',
                      {'task': task, 'comments': comments})


class SubtaskCreateView(LoginRequiredMixin, View):
    """HTMX — create subtask from AI suggestion or manual input. Returns subtask list."""
    def post(self, request, pk):
        parent = get_object_or_404(Task, pk=pk)
        if not parent.project.is_member(request.user):
            raise PermissionDenied
        title  = request.POST.get('title', '').strip()
        if title:
            Task.objects.create(
                title      = title,
                project    = parent.project,
                parent_task= parent,
                status     = Task.STATUS_TODO,
                created_by = request.user,
            )
        subtasks = parent.subtasks.all()
        return render(request, 'tasks/partials/subtask_list.html',
                      {'task': parent, 'subtasks': subtasks})


class SubtaskCheckView(LoginRequiredMixin, View):
    """HTMX — toggle subtask completion. Returns subtask row partial."""
    def post(self, request, pk, sub_pk):
        parent = get_object_or_404(Task, pk=pk)
        subtask = get_object_or_404(Task, pk=sub_pk, parent_task=parent)
        if not parent.project.is_member(request.user):
            raise PermissionDenied
        # Toggle between TODO and DONE
        if subtask.status == Task.STATUS_DONE:
            subtask.status = Task.STATUS_TODO
        else:
            subtask.status = Task.STATUS_DONE
        subtask.save(update_fields=['status'])
        subtasks = parent.subtasks.all()
        return render(request, 'tasks/partials/subtask_list.html',
                      {'task': parent, 'subtasks': subtasks})


class CommentDeleteView(LoginRequiredMixin, View):
    """HTMX — delete own comment. Returns updated comment list."""
    def post(self, request, comment_pk):
        comment = get_object_or_404(Comment, pk=comment_pk)
        task = comment.task
        if not task.project.is_member(request.user):
            raise PermissionDenied
        # Only comment author can delete
        if comment.author != request.user:
            raise PermissionDenied
        comment.delete()
        comments = task.comments.select_related('author').order_by('created_at')
        return render(request, 'tasks/partials/comment_list.html',
                      {'task': task, 'comments': comments})


class TaskEditFieldView(LoginRequiredMixin, View):
    """
    HTMX inline field editor.
    Accepts: title, description, due_date, priority, status, requester
    Returns: updated field partial
    """
    EDITABLE_FIELDS = ['title', 'description', 'due_date', 'priority', 'status', 'requester']

    def get(self, request, pk):
        """Return edit or view mode partial based on ?mode= parameter."""
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        mode = request.GET.get('mode', 'view')
        field = request.GET.get('field', 'title')

        if field not in self.EDITABLE_FIELDS:
            return HttpResponseBadRequest(f'Field "{field}" is not editable.')

        # Add project members for requester field dropdown
        context = {'task': task, 'mode': mode}
        if field == 'requester':
            context['project_members'] = task.project.get_all_members()

        template_name = f'tasks/partials/field_{field}.html'
        return render(request, template_name, context)

    def post(self, request, pk):
        """Update field value and return view mode partial."""
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        field = request.POST.get('field')
        value = request.POST.get('value', '').strip()

        if field not in self.EDITABLE_FIELDS:
            return HttpResponseBadRequest(f'Field "{field}" is not editable.')

        if field == 'title' and not value:
            return HttpResponseBadRequest('Title cannot be empty.')

        # Special handling for FK fields
        if field == 'requester':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            task.requester = User.objects.filter(pk=value).first() if value else None
            task.save(update_fields=['requester'])
        else:
            setattr(task, field, value or None)
            task.save(update_fields=[field])

        return render(request, f'tasks/partials/field_{field}.html', {'task': task, 'mode': 'view'})


class TaskDetailFullView(LoginRequiredMixin, View):
    """
    Full-page task detail — renders in the main content area.
    Same data as slide-over but uses a different template with more space.
    """
    def get(self, request, pk):
        task = get_object_or_404(
            Task.objects.select_related(
                'project', 'created_by',
                'assigned_to_user', 'assigned_to_team', 'parent_task',
            ).prefetch_related(
                'subtasks', 'labels', 'comments__author',
                'attachments__uploaded_by',
                'watching_users', 'watching_teams',
                'time_entries__user',
            ),
            pk=pk
        )
        if not task.project.is_member(request.user):
            raise PermissionDenied

        return render(request, 'tasks/detail_full.html', {
            'task':            task,
            'project_members': task.project.get_all_members(),
            'project_teams':   task.project.team_members.all(),
            'is_watching':     request.user in task.get_all_watchers(),
            'total_time_m':    task.time_entries.aggregate(t=Sum('duration_m'))['t'] or 0,
            'user_role':       task.project.get_effective_role(request.user),
            'project_tasks':   task.project.tasks.exclude(pk=task.pk).order_by('title'),
            'breadcrumb': [
                {'label': 'Projects',      'url': reverse('projects:project-list')},
                {'label': task.project.name, 'url': reverse('projects:project-detail', args=[task.project.pk])},
                {'label': task.title,      'url': None},
            ]
        })


class AttachmentUploadView(LoginRequiredMixin, View):
    """
    HTMX file upload — returns updated attachment list partial.
    Accepts multipart/form-data.
    """
    MAX_SIZE_MB = 25

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        file = request.FILES.get('file')
        if not file:
            return HttpResponseBadRequest('No file provided.')

        # Size check
        if file.size > self.MAX_SIZE_MB * 1024 * 1024:
            return HttpResponseBadRequest(f'File exceeds {self.MAX_SIZE_MB}MB limit.')

        attachment = Attachment.objects.create(
            task        = task,
            uploaded_by = request.user,
            file        = file,
            filename    = file.name,
            size_bytes  = file.size,
        )

        attachments = task.attachments.select_related('uploaded_by').order_by('-created_at')
        return render(request, 'tasks/partials/attachment_list.html',
                      {'task': task, 'attachments': attachments})


class AttachmentDeleteView(LoginRequiredMixin, View):
    """
    HTMX — delete attachment (uploader or project manager only).
    Returns updated attachment list.
    """
    def post(self, request, att_pk):
        att = get_object_or_404(Attachment, pk=att_pk)

        is_uploader = att.uploaded_by == request.user
        is_manager  = att.task.project.get_effective_role(request.user) == 'manager'

        if not (is_uploader or is_manager):
            raise PermissionDenied

        att.file.delete(save=False)  # delete from filesystem
        att.delete()

        attachments = att.task.attachments.select_related('uploaded_by').order_by('-created_at')
        return render(request, 'tasks/partials/attachment_list.html',
                      {'task': att.task, 'attachments': attachments})


class AttachmentDownloadView(LoginRequiredMixin, View):
    """Serve file as download (respects project membership)."""
    def get(self, request, att_pk):
        att = get_object_or_404(Attachment, pk=att_pk)
        if not att.task.project.is_member(request.user):
            raise PermissionDenied
        return FileResponse(att.file.open('rb'),
                            as_attachment=True,
                            filename=att.filename)


class TimeEntryLogView(LoginRequiredMixin, View):
    """HTMX — log time on a task, return updated time entry list."""
    def post(self, request, pk):
        task       = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        duration_m = int(request.POST.get('duration_m', 0))
        note       = request.POST.get('note', '').strip()

        if duration_m > 0:
            TimeEntry.objects.create(
                task       = task,
                user       = request.user,
                started_at = timezone.now(),
                duration_m = duration_m,
                note       = note,
            )

        entries    = task.time_entries.select_related('user').order_by('-started_at')
        total_m    = entries.aggregate(t=Sum('duration_m'))['t'] or 0
        return render(request, 'tasks/partials/time_entry_list.html',
                      {'task': task, 'entries': entries, 'total_m': total_m})


class TimeEntryDeleteView(LoginRequiredMixin, View):
    """HTMX — delete own time entry, return updated list."""
    def post(self, request, entry_pk):
        entry = get_object_or_404(TimeEntry, pk=entry_pk, user=request.user)
        task  = entry.task
        if not task.project.is_member(request.user):
            raise PermissionDenied
        entry.delete()
        entries = task.time_entries.select_related('user').order_by('-started_at')
        total_m = entries.aggregate(t=Sum('duration_m'))['t'] or 0
        return render(request, 'tasks/partials/time_entry_list.html',
                      {'task': task, 'entries': entries, 'total_m': total_m})


class TaskCloseFormView(LoginRequiredMixin, View):
    """HTMX GET — returns modal content for closing a task with time tracking."""
    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        return render(request, 'tasks/partials/close_form.html', {'task': task})


class TaskCloseView(LoginRequiredMixin, View):
    """
    POST — Close task with time tracking.
    Required field: actual_hours (actual effort in hours)
    """
    def post(self, request, pk):
        from django.conf import settings

        task         = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        actual_hours = request.POST.get('actual_hours', '').strip()
        note         = request.POST.get('note', '').strip()

        if not actual_hours:
            return render(request, 'tasks/partials/close_form.html', {
                'task':  task,
                'error': 'Bitte den tatsächlichen Aufwand angeben.',
            })

        try:
            hours = float(actual_hours.replace(',', '.'))
            if hours < 0:
                raise ValueError
        except ValueError:
            return render(request, 'tasks/partials/close_form.html', {
                'task':  task,
                'error': 'Bitte eine gültige Stundenanzahl eingeben.',
            })

        # Create Time Entry
        TimeEntry.objects.create(
            task       = task,
            user       = request.user,
            started_at = timezone.now(),
            duration_m = int(hours * 60),
            note       = note or f'Abschluss-Erfassung von {request.user.full_name}',
        )

        # Set Task to Done
        old_status  = task.status
        task.status = Task.STATUS_DONE
        task.save(update_fields=['status'])

        # Send Mail
        from apps.mail.dispatcher import dispatch
        from apps.mail.models import MailHook

        context = {
            'task_title':   task.title,
            'task_url':     f'{settings.SITE_URL}/tasks/{task.pk}/',
            'project_name': task.project.name,
            'closed_by':    request.user.full_name,
            'actual_hours': hours,
            'note':         note,
        }

        # To Requester (if exists and not current user)
        if task.effective_requester and task.effective_requester != request.user:
            dispatch(
                event=MailHook.EVENT_TASK_DONE,
                context={
                    **context,
                    'recipient_name': task.effective_requester.full_name,
                },
                recipients_override=[task.effective_requester.email],
            )

        # To Watchers
        dispatch(
            event=MailHook.EVENT_TASK_DONE,
            context=context,
            task=task,
        )

        # Portal User Done Notification (ISSUE-28)
        if task.created_by and hasattr(task.created_by, 'is_portal_user') and task.created_by.is_portal_user:
            from apps.portal.tasks import send_portal_ticket_done_notification
            send_portal_ticket_done_notification.delay(task.pk)

        # Close modal + trigger refresh
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'taskClosed'
        return response


class TaskAssignFormView(LoginRequiredMixin, View):
    """HTMX GET — returns assignment modal content."""
    def get(self, request, pk):
        from apps.teams.models import Team

        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        return render(request, 'tasks/partials/assign_form.html', {
            'task':            task,
            'project_members': task.project.get_all_members().order_by('display_name'),
            'project_teams':   Team.objects.filter(
                models.Q(projectteammembership__project=task.project) |
                models.Q(is_global=True),
                is_active=True
            ).distinct().order_by('name'),
        })


class TaskCloneView(LoginRequiredMixin, View):
    """
    POST — clone a task and redirect to the new task's detail page.
    Clones: title (prefixed), description, priority, labels,
            assigned_to_user, assigned_to_team, due_date, deadline,
            estimated_h, client.
    Does NOT clone: status (reset to backlog), time entries,
                    comments, attachments, watchers.
    Optionally clones subtasks if ?include_subtasks=1.
    """
    def post(self, request, pk):
        original = get_object_or_404(Task, pk=pk)

        if not original.project.is_member(request.user):
            raise PermissionDenied

        include_subtasks = request.POST.get('include_subtasks') == '1'

        # Clone the task
        clone = Task.objects.create(
            title            = f'[Kopie] {original.title}',
            description      = original.description,
            project          = original.project,
            status           = Task.STATUS_BACKLOG,
            priority         = original.priority,
            created_by       = request.user,
            assigned_to_user = original.assigned_to_user,
            assigned_to_team = original.assigned_to_team,
            due_date         = original.due_date,
            deadline         = original.deadline,
            estimated_h      = original.estimated_h,
            client           = original.client,
        )

        # Copy labels (M2M)
        clone.labels.set(original.labels.all())

        # Optionally clone subtasks
        if include_subtasks:
            for subtask in original.subtasks.all():
                Task.objects.create(
                    title            = subtask.title,
                    description      = subtask.description,
                    project          = clone.project,
                    status           = Task.STATUS_BACKLOG,
                    priority         = subtask.priority,
                    created_by       = request.user,
                    assigned_to_user = subtask.assigned_to_user,
                    assigned_to_team = subtask.assigned_to_team,
                    parent_task      = clone,
                    client           = subtask.client,
                )

        # HTMX or full page
        if request.htmx:
            return render(request, 'tasks/partials/card.html', {'task': clone})

        return redirect('tasks:task-detail-full', pk=clone.pk)


class DependencyAddView(LoginRequiredMixin, View):
    """
    HTMX — add a "blocked by" dependency.
    POST: { blocked_by_id: <task_id> }
    Returns updated dependency list partial.
    """
    def post(self, request, pk):
        from .models import TaskDependency
        task         = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        blocked_by_id = request.POST.get('blocked_by_id')
        if not blocked_by_id:
            return HttpResponseBadRequest('blocked_by_id is required.')
        blocked_by   = get_object_or_404(Task, pk=blocked_by_id)

        # Prevent self-dependency
        if task.pk == blocked_by.pk:
            return HttpResponseBadRequest('A task cannot depend on itself.')

        # Prevent circular dependency (simple check)
        if blocked_by.is_blocked and task in blocked_by.blocking_tasks:
            return HttpResponseBadRequest('Circular dependency detected.')

        TaskDependency.objects.get_or_create(
            task=task, blocked_by=blocked_by,
            defaults={'created_by': request.user}
        )

        # Get project_tasks for the form
        project_tasks = task.project.tasks.exclude(pk=task.pk).order_by('title')
        return render(request, 'tasks/partials/dependency_list.html',
                      {'task': task, 'project_tasks': project_tasks})


class DependencyRemoveView(LoginRequiredMixin, View):
    """HTMX — remove a dependency. Returns updated list."""
    def post(self, request, pk, dep_pk):
        from .models import TaskDependency
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        TaskDependency.objects.filter(task=task, pk=dep_pk).delete()
        # Get project_tasks for the form
        project_tasks = task.project.tasks.exclude(pk=task.pk).order_by('title')
        return render(request, 'tasks/partials/dependency_list.html',
                      {'task': task, 'project_tasks': project_tasks})


# ==================== TaskTemplate Views ====================

class TemplateListView(LoginRequiredMixin, View):
    """Alle aktiven Templates — für interne User."""
    def get(self, request):
        from .models import TaskTemplate
        templates = TaskTemplate.objects.filter(
            is_active=True
        ).select_related('default_project', 'default_assigned_to_team', 'client')
        return render(request, 'tasks/templates/list.html', {
            'templates': templates,
        })


class TemplateDetailView(LoginRequiredMixin, View):
    """Template detail view."""
    def get(self, request, slug):
        from .models import TaskTemplate
        template = get_object_or_404(TaskTemplate, slug=slug, is_active=True)
        extra_fields = template.get_extra_fields()
        return render(request, 'tasks/templates/detail.html', {
            'template': template,
            'extra_fields': extra_fields,
        })


class TemplateCreateView(View):
    """Create a new template — staff only."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        from apps.projects.models import Project
        from apps.teams.models import Team
        from apps.core.models import Client
        projects = Project.objects.exclude(status='archived').order_by('name')
        teams    = Team.objects.filter(is_active=True).order_by('name')
        clients  = Client.objects.filter(is_active=True).order_by('name')
        return render(request, 'tasks/templates/form.html', {
            'projects': projects, 'teams': teams, 'clients': clients,
            'priority_choices': Task.PRIORITY_CHOICES,
        })

    def post(self, request):
        from .models import TaskTemplate
        from apps.projects.models import Project
        from apps.teams.models import Team
        from apps.core.models import Client

        name     = request.POST.get('name', '').strip()
        yaml_str = request.POST.get('extra_fields_yaml', '').strip()

        if not name:
            projects = Project.objects.exclude(status='archived').order_by('name')
            teams    = Team.objects.filter(is_active=True).order_by('name')
            clients  = Client.objects.filter(is_active=True).order_by('name')
            return render(request, 'tasks/templates/form.html', {
                'error': 'Name ist ein Pflichtfeld.',
                'post': request.POST,
                'projects': projects,
                'teams': teams,
                'clients': clients,
                'priority_choices': Task.PRIORITY_CHOICES,
            })

        template = TaskTemplate(
            name                    = name,
            description             = request.POST.get('description', ''),
            default_project_id      = request.POST.get('default_project') or None,
            default_priority        = int(request.POST.get('default_priority', 0)),
            default_assigned_to_team_id = request.POST.get('default_team') or None,
            extra_fields_yaml       = yaml_str,
            is_portal_visible       = 'is_portal_visible' in request.POST,
            client_id               = request.POST.get('client') or None,
            created_by              = request.user,
        )

        # YAML validieren
        valid, error = template.validate_yaml()
        if not valid:
            projects = Project.objects.exclude(status='archived').order_by('name')
            teams    = Team.objects.filter(is_active=True).order_by('name')
            clients  = Client.objects.filter(is_active=True).order_by('name')
            return render(request, 'tasks/templates/form.html', {
                'error': error, 'post': request.POST,
                'projects': projects,
                'teams': teams,
                'clients': clients,
                'priority_choices': Task.PRIORITY_CHOICES,
            })

        # Slug generieren
        from django.utils.text import slugify
        slug = slugify(name)
        base, n = slug, 1
        while TaskTemplate.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'; n += 1
        template.slug = slug
        template.save()

        return redirect('tasks:template-detail', slug=template.slug)


class TemplateEditView(View):
    """Edit an existing template — staff only."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug):
        from .models import TaskTemplate
        from apps.projects.models import Project
        from apps.teams.models import Team
        from apps.core.models import Client

        template = get_object_or_404(TaskTemplate, slug=slug)
        projects = Project.objects.exclude(status='archived').order_by('name')
        teams    = Team.objects.filter(is_active=True).order_by('name')
        clients  = Client.objects.filter(is_active=True).order_by('name')

        return render(request, 'tasks/templates/form.html', {
            'template': template,
            'projects': projects,
            'teams': teams,
            'clients': clients,
            'priority_choices': Task.PRIORITY_CHOICES,
        })

    def post(self, request, slug):
        from .models import TaskTemplate
        from apps.projects.models import Project
        from apps.teams.models import Team
        from apps.core.models import Client

        template = get_object_or_404(TaskTemplate, slug=slug)

        name     = request.POST.get('name', '').strip()
        yaml_str = request.POST.get('extra_fields_yaml', '').strip()

        if not name:
            projects = Project.objects.exclude(status='archived').order_by('name')
            teams    = Team.objects.filter(is_active=True).order_by('name')
            clients  = Client.objects.filter(is_active=True).order_by('name')
            return render(request, 'tasks/templates/form.html', {
                'error': 'Name ist ein Pflichtfeld.',
                'template': template,
                'post': request.POST,
                'projects': projects,
                'teams': teams,
                'clients': clients,
                'priority_choices': Task.PRIORITY_CHOICES,
            })

        template.name                    = name
        template.description             = request.POST.get('description', '')
        template.default_project_id      = request.POST.get('default_project') or None
        template.default_priority        = int(request.POST.get('default_priority', 0))
        template.default_assigned_to_team_id = request.POST.get('default_team') or None
        template.extra_fields_yaml       = yaml_str
        template.is_portal_visible       = 'is_portal_visible' in request.POST
        template.client_id               = request.POST.get('client') or None

        # YAML validieren
        valid, error = template.validate_yaml()
        if not valid:
            projects = Project.objects.exclude(status='archived').order_by('name')
            teams    = Team.objects.filter(is_active=True).order_by('name')
            clients  = Client.objects.filter(is_active=True).order_by('name')
            return render(request, 'tasks/templates/form.html', {
                'error': error,
                'template': template,
                'post': request.POST,
                'projects': projects,
                'teams': teams,
                'clients': clients,
                'priority_choices': Task.PRIORITY_CHOICES,
            })

        # Update slug if name changed
        if template.name != name:
            from django.utils.text import slugify
            slug = slugify(name)
            base, n = slug, 1
            while TaskTemplate.objects.filter(slug=slug).exclude(pk=template.pk).exists():
                slug = f'{base}-{n}'; n += 1
            template.slug = slug

        template.save()
        return redirect('tasks:template-detail', slug=template.slug)


class TemplateUseView(LoginRequiredMixin, View):
    """
    GET  → rendert das Template-Formular (Standard + Zusatzfelder)
    POST → erstellt einen Task aus dem Template
    """
    def get(self, request, slug):
        from .models import TaskTemplate
        from apps.projects.models import Project

        template = get_object_or_404(TaskTemplate, slug=slug, is_active=True)
        extra_fields = template.get_extra_fields()

        # Zugängliche Projekte
        user     = request.user
        my_teams = user.team_memberships.all().values_list('team', flat=True)
        projects = Project.objects.filter(
            models.Q(projectusermembership__user=user) |
            models.Q(projectteammembership__team__in=my_teams)
        ).exclude(status='archived').distinct().order_by('name')

        return render(request, 'tasks/templates/use.html', {
            'template':    template,
            'extra_fields': extra_fields,
            'projects':    projects,
            'priority_choices': Task.PRIORITY_CHOICES,
        })

    def post(self, request, slug):
        from .models import TaskTemplate
        from apps.projects.models import Project
        from apps.tasks.template_utils import (
            validate_extra_fields,
            render_extra_fields_to_description,
        )

        template     = get_object_or_404(TaskTemplate, slug=slug, is_active=True)
        extra_fields = template.get_extra_fields()

        # Zusatzfelder validieren
        errors = validate_extra_fields(extra_fields, request.POST)

        title = request.POST.get('title', '').strip()
        if not title:
            errors.insert(0, 'Titel ist ein Pflichtfeld.')

        project_id = request.POST.get('project') or template.default_project_id
        if not project_id:
            errors.insert(0, 'Projekt ist ein Pflichtfeld.')

        if errors:
            user     = request.user
            my_teams = user.team_memberships.all().values_list('team', flat=True)
            projects = Project.objects.filter(
                models.Q(projectusermembership__user=user) |
                models.Q(projectteammembership__team__in=my_teams)
            ).exclude(status='archived').distinct().order_by('name')
            return render(request, 'tasks/templates/use.html', {
                'template':     template,
                'extra_fields': extra_fields,
                'errors':       errors,
                'projects':     projects,
                'post':         request.POST,
                'priority_choices': Task.PRIORITY_CHOICES,
            })

        # Beschreibung aus Zusatzfeldern aufbauen
        extra_description = render_extra_fields_to_description(
            extra_fields, request.POST
        )
        manual_description = request.POST.get('description', '').strip()

        # Beschreibung zusammensetzen
        if manual_description and extra_description:
            full_description = f'{extra_description}\n\n---\n\n{manual_description}'
        else:
            full_description = extra_description or manual_description

        project = get_object_or_404(Project, pk=project_id)

        if not project.is_member(request.user):
            raise PermissionDenied

        task = Task.objects.create(
            title       = title,
            description = full_description,
            project     = project,
            priority    = int(request.POST.get('priority', template.default_priority)),
            due_date    = request.POST.get('due_date') or None,
            deadline    = request.POST.get('deadline') or None,
            created_by  = request.user,
            requester   = request.user,
            client      = template.client or project.client,
            assigned_to_team = template.default_assigned_to_team,
            template    = template,
        )

        return redirect('tasks:task-detail-full', pk=task.pk)


class TemplatePreviewView(LoginRequiredMixin, View):
    """
    HTMX — live Vorschau des generierten Beschreibungsblocks.
    Wird beim Ausfüllen des Formulars aufgerufen.
    """
    def post(self, request, slug):
        from .models import TaskTemplate
        from apps.tasks.template_utils import render_extra_fields_to_description

        template     = get_object_or_404(TaskTemplate, slug=slug)
        extra_fields = template.get_extra_fields()

        preview = render_extra_fields_to_description(extra_fields, request.POST)

        return render(request, 'tasks/templates/partials/description_preview.html', {
            'preview': preview,
        })
