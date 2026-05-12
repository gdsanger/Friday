"""
AI views for Friday project.
HTMX AI Action Endpoints.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from .service import ai_service
from .exceptions import AIServiceDisabledError, AIBudgetExceededError, AIProviderError


class TaskAIActionView(LoginRequiredMixin, View):
    """
    Handles all AI actions on a Task.
    URL: POST /tasks/<task_id>/ai/<action>/
    Returns HTMX partial.
    """
    async def post(self, request, task_id, action):
        """Handle POST request for AI actions."""
        from apps.tasks.models import Task
        task = get_object_or_404(Task, pk=task_id)

        # Permission: user must be project member
        if not task.project.is_member(request.user):
            return TemplateResponse(request, 'ai/partials/error.html',
                                    {'error': 'Access denied.'}, status=403)
        try:
            if action == 'summarize':
                result = await ai_service.summarize_task(task, user=request.user)
                return TemplateResponse(request, 'ai/partials/summary.html',
                                        {'summary': result, 'task': task})

            elif action == 'subtasks':
                suggestions = await ai_service.suggest_subtasks(task, user=request.user)
                return TemplateResponse(request, 'ai/partials/subtask_suggestions.html',
                                        {'suggestions': suggestions, 'task': task})

            elif action == 'description':
                description = await ai_service.generate_task_description(
                    task.title, user=request.user
                )
                return TemplateResponse(request, 'ai/partials/description.html',
                                        {'description': description, 'task': task})

            else:
                return TemplateResponse(request, 'ai/partials/error.html',
                                        {'error': f'Unknown AI action: {action}'}, status=400)

        except AIServiceDisabledError:
            return TemplateResponse(request, 'ai/partials/error.html',
                                    {'error': 'AI service is currently unavailable.'})
        except AIBudgetExceededError:
            return TemplateResponse(request, 'ai/partials/error.html',
                                    {'error': 'Daily AI limit reached. Resets at midnight.'})
        except AIProviderError as e:
            return TemplateResponse(request, 'ai/partials/error.html',
                                    {'error': 'AI providers unavailable. Please try later.'})

