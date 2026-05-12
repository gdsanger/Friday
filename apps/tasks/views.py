"""
Task views for Friday project.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View

from .models import Task, Comment

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

        ctx = {
            'task': task,
            'project_members': task.project.get_all_members(),
            'project_teams':   task.project.team_members.all(),
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
        Optional: ?project=<id> pre-selects the project.
        Optional: ?status=<status> pre-selects the status column.
        """
        from apps.projects.models import Project

        project_id = request.GET.get('project_id') or request.GET.get('project')
        status     = request.GET.get('status', Task.STATUS_BACKLOG)

        # Only show projects the user is a member of
        accessible_projects = Project.objects.filter(
            models.Q(user_members=request.user) |
            models.Q(team_members__in=request.user.teams)
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

        # Return quick-add form for HTMX, full form for regular requests
        if request.htmx:
            return render(request, 'tasks/partials/quick_add_form.html', ctx)
        return render(request, 'tasks/create.html', ctx)

    def post(self, request):
        """
        Handles both:
        - Full page form submission (non-HTMX) → redirect to task detail
        - HTMX quick-add from Kanban column → return card partial
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

        # HTMX quick-add from Kanban → return card partial
        if request.htmx:
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
