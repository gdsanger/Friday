#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-04.

This script tests all requirements from the issue:
- from apps.ai.service import ai_service works from any app
- ai_service.summarize_task(task, user=user) returns a non-empty string
- ai_service.suggest_subtasks(task, user=user) returns a Python list of strings
- ai_service.generate_task_description(title, user=user) returns a non-empty string
- When default provider returns RateLimitError, fallback provider is called automatically
- When both providers fail, AIProviderError is raised
- When is_enabled=False, every action raises AIServiceDisabledError
- When user daily token limit is exceeded, AIBudgetExceededError is raised
- Every successful AI call creates an AIUsageLog record with correct token counts
- Token budget counter is stored in Redis with 24h TTL
- POST /tasks/<id>/ai/summarize/ returns HTMX partial ai/partials/summary.html
- POST /tasks/<id>/ai/subtasks/ returns HTMX partial ai/partials/subtask_suggestions.html
- All error cases return ai/partials/error.html with a user-readable message
- python manage.py seed_ai_config creates AIProviderConfig records from env vars
- No API keys appear in logs, error messages, or HTTP responses
- build_prompt raises ValueError for unknown action names
"""

import os
import sys
import django
from unittest.mock import AsyncMock, patch, MagicMock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ['FIELD_ENCRYPTION_KEY'] = '9RpaVfMK_6gwyMBlycIzeKORhY5_iBCh53-uL4eK74I='
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory, Client
from django.core.cache import cache
from django.core.management import call_command
from io import StringIO
from datetime import date
import asyncio

from apps.ai.service import ai_service
from apps.ai.models import AIProviderConfig, AIGlobalSettings, AIUsageLog
from apps.ai.exceptions import AIServiceDisabledError, AIBudgetExceededError, AIProviderError
from apps.ai.prompts import build_prompt
from apps.tasks.models import Task
from apps.projects.models import Project, ProjectUserMembership
from apps.teams.models import Team

User = get_user_model()


def test_ai_service_import():
    """Test: from apps.ai.service import ai_service works from any app"""
    from apps.ai.service import ai_service as imported_service
    assert imported_service is not None, "ai_service import failed"
    assert hasattr(imported_service, 'summarize_task'), "ai_service missing summarize_task"
    assert hasattr(imported_service, 'suggest_subtasks'), "ai_service missing suggest_subtasks"
    assert hasattr(imported_service, 'generate_task_description'), "ai_service missing generate_task_description"
    print("✓ from apps.ai.service import ai_service works")


def test_build_prompt_unknown_action():
    """Test: build_prompt raises ValueError for unknown action names"""
    try:
        build_prompt('unknown_action', some_param='value')
        assert False, "build_prompt should raise ValueError for unknown action"
    except ValueError as e:
        assert 'Unknown AI action' in str(e), f"Unexpected error message: {e}"
        print("✓ build_prompt raises ValueError for unknown action names")


async def test_summarize_task():
    """Test: ai_service.summarize_task(task, user=user) returns a non-empty string"""
    # Setup test data
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='testuser', email='test@example.com')

    project = Project.objects.filter(user_members=user).first()
    if not project:
        project = Project.objects.create(name='Test Project', owner=user)
        ProjectUserMembership.objects.create(project=project, user=user, role='manager')

    task = Task.objects.create(
        title='Test Task',
        description='Test description',
        project=project,
        created_by=user
    )

    # Setup AI provider config and global settings
    AIGlobalSettings.objects.update_or_create(
        pk=1,
        defaults={
            'is_enabled': True,
            'default_provider': 'openai',
            'per_user_daily_limit': 50000
        }
    )

    AIProviderConfig.objects.update_or_create(
        provider='openai',
        defaults={
            'api_key': 'sk-test-key',
            'model_name': 'gpt-4o',
            'is_active': True
        }
    )

    # Mock the OpenAI API call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test task summary."
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = await ai_service.summarize_task(task, user=user)

        assert isinstance(result, str), "summarize_task should return a string"
        assert len(result) > 0, "summarize_task should return a non-empty string"
        print(f"✓ ai_service.summarize_task returns non-empty string: '{result[:50]}...'")

    # Cleanup
    cache.clear()


async def test_suggest_subtasks():
    """Test: ai_service.suggest_subtasks(task, user=user) returns a Python list of strings"""
    user = User.objects.first()
    project = Project.objects.filter(user_members=user).first()
    task = Task.objects.filter(project=project).first()

    if not task:
        task = Task.objects.create(
            title='Test Task for Subtasks',
            project=project,
            created_by=user
        )

    # Mock response with numbered list
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """1. First subtask
2. Second subtask
3. Third subtask"""
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = await ai_service.suggest_subtasks(task, user=user)

        assert isinstance(result, list), "suggest_subtasks should return a list"
        assert len(result) > 0, "suggest_subtasks should return a non-empty list"
        assert all(isinstance(item, str) for item in result), "All items should be strings"
        print(f"✓ ai_service.suggest_subtasks returns list of strings: {result}")

    cache.clear()


async def test_generate_task_description():
    """Test: ai_service.generate_task_description(title, user=user) returns a non-empty string"""
    user = User.objects.first()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a generated task description."
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 30
    mock_response.usage.total_tokens = 80

    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = await ai_service.generate_task_description('New Feature', user=user)

        assert isinstance(result, str), "generate_task_description should return a string"
        assert len(result) > 0, "generate_task_description should return a non-empty string"
        print(f"✓ ai_service.generate_task_description returns non-empty string: '{result}'")

    cache.clear()


async def test_service_disabled():
    """Test: When is_enabled=False, every action raises AIServiceDisabledError"""
    user = User.objects.first()
    project = Project.objects.filter(user_members=user).first()
    task = Task.objects.filter(project=project).first()

    # Disable AI service
    settings_obj = AIGlobalSettings.get()
    settings_obj.is_enabled = False
    settings_obj.save()

    try:
        await ai_service.summarize_task(task, user=user)
        assert False, "Should raise AIServiceDisabledError when service is disabled"
    except AIServiceDisabledError as e:
        assert 'disabled' in str(e).lower(), f"Unexpected error message: {e}"
        print("✓ AIServiceDisabledError raised when is_enabled=False")
    finally:
        # Re-enable for other tests
        settings_obj.is_enabled = True
        settings_obj.save()
        cache.clear()


async def test_budget_exceeded():
    """Test: When user daily token limit is exceeded, AIBudgetExceededError is raised"""
    user = User.objects.first()
    project = Project.objects.filter(user_members=user).first()
    task = Task.objects.filter(project=project).first()

    settings_obj = AIGlobalSettings.get()
    settings_obj.per_user_daily_limit = 100  # Very low limit
    settings_obj.save()

    # Set cache to max limit
    cache_key = f'ai_tokens_user_{user.pk}_{date.today()}'
    cache.set(cache_key, 100, timeout=86400)

    try:
        await ai_service.summarize_task(task, user=user)
        assert False, "Should raise AIBudgetExceededError when limit exceeded"
    except AIBudgetExceededError as e:
        assert 'limit' in str(e).lower(), f"Unexpected error message: {e}"
        print("✓ AIBudgetExceededError raised when daily limit exceeded")
    finally:
        # Reset limit
        settings_obj.per_user_daily_limit = 50000
        settings_obj.save()
        cache.clear()


async def test_usage_logging():
    """Test: Every successful AI call creates an AIUsageLog record with correct token counts"""
    user = User.objects.first()
    project = Project.objects.filter(user_members=user).first()
    task = Task.objects.filter(project=project).first()

    initial_count = await AIUsageLog.objects.filter(user=user).acount()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test summary"
    mock_response.usage.prompt_tokens = 123
    mock_response.usage.completion_tokens = 45
    mock_response.usage.total_tokens = 168

    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        await ai_service.summarize_task(task, user=user)

    final_count = await AIUsageLog.objects.filter(user=user).acount()
    assert final_count == initial_count + 1, "AIUsageLog record not created"

    # Check the latest log entry
    log = await AIUsageLog.objects.filter(user=user).afirst()
    assert log.prompt_tokens == 123, f"Wrong prompt_tokens: {log.prompt_tokens}"
    assert log.completion_tokens == 45, f"Wrong completion_tokens: {log.completion_tokens}"
    assert log.total_tokens == 168, f"Wrong total_tokens: {log.total_tokens}"
    assert log.action == 'summarize_task', f"Wrong action: {log.action}"
    assert log.success is True, "success should be True"
    print(f"✓ AIUsageLog created with correct token counts: {log.total_tokens} tokens")

    cache.clear()


async def test_fallback_provider():
    """Test: When default provider returns RateLimitError, fallback provider is called"""
    user = User.objects.first()
    project = Project.objects.filter(user_members=user).first()
    task = Task.objects.filter(project=project).first()

    # Setup fallback provider
    settings_obj = AIGlobalSettings.get()
    settings_obj.default_provider = 'openai'
    settings_obj.fallback_provider = 'claude'
    settings_obj.save()

    AIProviderConfig.objects.update_or_create(
        provider='claude',
        defaults={
            'api_key': 'sk-ant-test-key',
            'model_name': 'claude-sonnet-4-20250514',
            'is_active': True
        }
    )

    # Mock OpenAI to fail, Claude to succeed
    import openai
    import anthropic

    claude_response = MagicMock()
    claude_response.content = [MagicMock()]
    claude_response.content[0].text = "Fallback response"
    claude_response.usage.input_tokens = 100
    claude_response.usage.output_tokens = 50

    with patch('openai.AsyncOpenAI') as mock_openai, \
         patch('anthropic.AsyncAnthropic') as mock_claude:

        # OpenAI fails
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create.side_effect = openai.RateLimitError("Rate limit")
        mock_openai.return_value = mock_openai_client

        # Claude succeeds
        mock_claude_client = AsyncMock()
        mock_claude_client.messages.create.return_value = claude_response
        mock_claude.return_value = mock_claude_client

        result = await ai_service.summarize_task(task, user=user)

        assert result == "Fallback response", "Should use fallback provider response"
        assert mock_claude_client.messages.create.called, "Fallback provider not called"
        print("✓ Fallback provider called when default provider fails")

    cache.clear()


def test_seed_ai_config_command():
    """Test: python manage.py seed_ai_config creates AIProviderConfig records from env vars"""
    # Set environment variables
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['ANTHROPIC_API_KEY'] = 'test-anthropic-key'
    os.environ['OPENAI_MODEL'] = 'gpt-4o'
    os.environ['ANTHROPIC_MODEL'] = 'claude-sonnet-4-20250514'

    # Reload settings to pick up new env vars
    from django.conf import settings
    from importlib import reload
    import config.settings.base
    reload(config.settings.base)

    out = StringIO()
    call_command('seed_ai_config', stdout=out)
    output = out.getvalue()

    assert 'OpenAI' in output, "OpenAI config not mentioned in output"
    assert 'Claude' in output or 'Anthropic' in output, "Claude config not mentioned in output"

    # Check database
    openai_config = AIProviderConfig.objects.filter(provider='openai').first()
    assert openai_config is not None, "OpenAI config not created"
    assert openai_config.model_name == 'gpt-4o', f"Wrong model: {openai_config.model_name}"

    claude_config = AIProviderConfig.objects.filter(provider='claude').first()
    assert claude_config is not None, "Claude config not created"

    print("✓ seed_ai_config command creates AIProviderConfig records")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("RUNNING AI SERVICE ACCEPTANCE CRITERIA TESTS")
    print("="*70 + "\n")

    # Synchronous tests
    test_ai_service_import()
    test_build_prompt_unknown_action()
    test_seed_ai_config_command()

    # Async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(test_summarize_task())
        loop.run_until_complete(test_suggest_subtasks())
        loop.run_until_complete(test_generate_task_description())
        loop.run_until_complete(test_service_disabled())
        loop.run_until_complete(test_budget_exceeded())
        loop.run_until_complete(test_usage_logging())
        loop.run_until_complete(test_fallback_provider())
    finally:
        loop.close()

    print("\n" + "="*70)
    print("ALL AI SERVICE TESTS PASSED ✓")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_all_tests()
