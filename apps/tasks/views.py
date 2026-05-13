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
        )

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
        if status in dict(Task.STATUS_CHOICES):
            task.status = status
        if position is not None:
            task.position = int(position)
        task.save(update_fields=['status', 'position'])
        return HttpResponse(status=204)


class TaskAssignView(LoginRequiredMixin, View):
    """HTMX — assign to user OR team (mutually exclusive). Returns assignee partial."""
    def post(self, request, pk):
        from apps.teams.models import Team
        task      = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied
        user_id   = request.POST.get('user_id')
        team_id   = request.POST.get('team_id')

        task.assigned_to_user = User.objects.get(pk=user_id) if user_id else None
        task.assigned_to_team = Team.objects.get(pk=team_id) if team_id else None
        task.save(update_fields=['assigned_to_user', 'assigned_to_team'])

        return render(request, 'tasks/partials/assignee.html', {'task': task})


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
    Accepts: title, description, due_date, priority, status
    Returns: updated field partial
    """
    EDITABLE_FIELDS = ['title', 'description', 'due_date', 'priority', 'status']

    def get(self, request, pk):
        """Return edit or view mode partial based on ?mode= parameter."""
        task = get_object_or_404(Task, pk=pk)
        if not task.project.is_member(request.user):
            raise PermissionDenied

        mode = request.GET.get('mode', 'view')
        field = request.GET.get('field', 'title')

        if field not in self.EDITABLE_FIELDS:
            return HttpResponseBadRequest(f'Field "{field}" is not editable.')

        template_name = f'tasks/partials/field_{field}.html'
        return render(request, template_name, {'task': task, 'mode': mode})

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
