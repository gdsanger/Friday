"""
Global AI Service for Friday project.
Platform-wide, provider-agnostic AI service.
"""
import time
import logging
from datetime import date
from django.core.cache import cache
from django.conf import settings
import openai
import anthropic

from .models import AIProviderConfig, AIGlobalSettings, AIUsageLog
from .exceptions import AIServiceDisabledError, AIBudgetExceededError, AIProviderError
from .prompts import build_prompt

logger = logging.getLogger('friday.ai')


class GlobalAIService:
    """
    Platform-wide AI service. Import and use the singleton:
        from apps.ai.service import ai_service
        result = await ai_service.summarize_task(task, user=request.user)
    """

    # ── Public Actions ────────────────────────────────────────────────────

    async def summarize_task(self, task, user) -> str:
        """Summarize a task based on its content and comments."""
        prompt = build_prompt('summarize_task', task=task)
        return await self._dispatch(prompt, action='summarize_task',
                                     user=user, obj=task, max_tokens=300)

    async def suggest_subtasks(self, task, user) -> list[str]:
        """Suggest subtasks for a given task."""
        prompt = build_prompt('suggest_subtasks', task=task)
        result = await self._dispatch(prompt, action='suggest_subtasks',
                                       user=user, obj=task, max_tokens=600)
        return self._parse_list(result)

    async def generate_task_description(self, title: str, user) -> str:
        """Generate a task description from a title."""
        prompt = build_prompt('task_description', title=title)
        return await self._dispatch(prompt, action='task_description',
                                     user=user, max_tokens=400)

    async def generate_project_report(self, project, user) -> str:
        """Generate a project status report."""
        prompt = build_prompt('project_report', project=project)
        return await self._dispatch(prompt, action='project_report',
                                     user=user, obj=project, max_tokens=1500)

    async def draft_mail_reply(self, mail_body: str, task_context: str, user) -> str:
        """Draft an email reply in the context of a task."""
        prompt = build_prompt('mail_reply', body=mail_body, context=task_context)
        return await self._dispatch(prompt, action='mail_reply',
                                     user=user, max_tokens=500)

    # ── Internal Dispatch ─────────────────────────────────────────────────

    async def _dispatch(self, prompt: str, action: str, user,
                         obj=None, max_tokens: int = 500) -> str:
        """Dispatch an AI request with fallback and budget checking."""
        settings_obj = await AIGlobalSettings.objects.aget(pk=1)

        if not settings_obj.is_enabled:
            raise AIServiceDisabledError('AI service is currently disabled.')

        await self._check_budget(user, settings_obj)

        provider = settings_obj.default_provider
        team = await self._get_user_team(user)
        start = time.monotonic()

        try:
            text, usage = await self._call_provider(provider, prompt, max_tokens)

        except (openai.RateLimitError, openai.APITimeoutError,
                anthropic.RateLimitError, anthropic.APITimeoutError) as exc:

            logger.warning(f'AI provider {provider} unavailable: {exc}. Trying fallback.')

            if not settings_obj.fallback_provider:
                raise AIProviderError(f'Provider {provider} unavailable, no fallback configured.')

            provider = settings_obj.fallback_provider
            text, usage = await self._call_provider(provider, prompt, max_tokens)
            usage['fallback_used'] = True

        await self._log_usage(user=user, team=team, provider=provider,
                               action=action, usage=usage, obj=obj)
        await self._increment_budget_counter(user, usage['total_tokens'])

        return text

    async def _call_provider(self, provider: str, prompt: str,
                               max_tokens: int) -> tuple[str, dict]:
        """Call the specified AI provider and return text + usage stats."""
        config = await AIProviderConfig.objects.aget(provider=provider, is_active=True)
        start = time.monotonic()

        if provider == AIProviderConfig.PROVIDER_OPENAI:
            client = openai.AsyncOpenAI(api_key=config.api_key)
            response = await client.chat.completions.create(
                model=config.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content, {
                'prompt_tokens':     response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens':      response.usage.total_tokens,
                'duration_ms':       int((time.monotonic() - start) * 1000),
            }

        elif provider == AIProviderConfig.PROVIDER_CLAUDE:
            client = anthropic.AsyncAnthropic(api_key=config.api_key)
            response = await client.messages.create(
                model=config.model_name,
                max_tokens=max_tokens,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return response.content[0].text, {
                'prompt_tokens':     response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens':      response.usage.input_tokens + response.usage.output_tokens,
                'duration_ms':       int((time.monotonic() - start) * 1000),
            }

        raise AIProviderError(f'Unknown provider: {provider}')

    # ── Budget & Usage ────────────────────────────────────────────────────

    async def _check_budget(self, user, settings_obj):
        """Check if user has remaining budget for today."""
        cache_key = f'ai_tokens_user_{user.pk}_{date.today()}'
        used = cache.get(cache_key, 0)
        if used >= settings_obj.per_user_daily_limit:
            raise AIBudgetExceededError(
                f'Daily AI token limit reached ({settings_obj.per_user_daily_limit} tokens). '
                'Resets at midnight.'
            )

    async def _increment_budget_counter(self, user, tokens: int):
        """Increment the user's daily token counter in Redis cache."""
        cache_key = f'ai_tokens_user_{user.pk}_{date.today()}'
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + tokens, timeout=86400)

    async def _log_usage(self, user, team, provider, action, usage, obj=None):
        """Log AI usage to database."""
        await AIUsageLog.objects.acreate(
            user=user,
            team=team,
            provider=provider,
            action=action,
            prompt_tokens=usage.get('prompt_tokens', 0),
            completion_tokens=usage.get('completion_tokens', 0),
            total_tokens=usage.get('total_tokens', 0),
            duration_ms=usage.get('duration_ms', 0),
            success=True,
            object_type=obj.__class__.__name__.lower() if obj else '',
            object_id=str(obj.pk) if obj else '',
        )

    async def _get_user_team(self, user):
        """Return user's primary team (Team Lead role preferred) or None."""
        membership = await user.team_memberships.select_related('team').afirst()
        return membership.team if membership else None

    # ── Utilities ─────────────────────────────────────────────────────────

    def _parse_list(self, text: str) -> list[str]:
        """Parse numbered or bulleted list from AI response into Python list."""
        import re
        lines = text.strip().split('\n')
        items = []
        for line in lines:
            line = re.sub(r'^[\d\.\-\*\•]+\s*', '', line.strip())
            if line:
                items.append(line)
        return items


# Module-level singleton — import this everywhere
ai_service = GlobalAIService()
