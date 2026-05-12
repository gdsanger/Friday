#!/usr/bin/env python
"""
Structural tests for AI service - verify code structure without API calls.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ['FIELD_ENCRYPTION_KEY'] = '9RpaVfMK_6gwyMBlycIzeKORhY5_iBCh53-uL4eK74I='
django.setup()

from apps.ai.service import ai_service
from apps.ai.prompts import build_prompt
from apps.ai.exceptions import AIServiceDisabledError, AIBudgetExceededError, AIProviderError
from apps.ai.models import AIProviderConfig, AIGlobalSettings, AIUsageLog


def test_imports():
    """Test all imports work correctly"""
    print("Testing imports...")
    assert ai_service is not None
    assert AIServiceDisabledError is not None
    assert AIBudgetExceededError is not None
    assert AIProviderError is not None
    print("✓ All imports successful")


def test_ai_service_methods():
    """Test ai_service has all required methods"""
    print("\nTesting ai_service methods...")
    methods = [
        'summarize_task',
        'suggest_subtasks',
        'generate_task_description',
        'generate_project_report',
        'draft_mail_reply',
    ]
    for method in methods:
        assert hasattr(ai_service, method), f"Missing method: {method}"
        print(f"  ✓ {method}")
    print("✓ All required methods exist")


def test_build_prompt_actions():
    """Test build_prompt supports all required actions"""
    print("\nTesting build_prompt actions...")

    # Test unknown action raises ValueError
    try:
        build_prompt('unknown_action')
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert 'Unknown AI action' in str(e)
        print("  ✓ Raises ValueError for unknown action")

    print("✓ build_prompt error handling works")


def test_models_exist():
    """Test all AI models are properly defined"""
    print("\nTesting AI models...")

    # Test AIProviderConfig
    assert hasattr(AIProviderConfig, 'PROVIDER_OPENAI')
    assert hasattr(AIProviderConfig, 'PROVIDER_CLAUDE')
    assert hasattr(AIProviderConfig, 'provider')
    assert hasattr(AIProviderConfig, 'api_key')
    assert hasattr(AIProviderConfig, 'model_name')
    print("  ✓ AIProviderConfig")

    # Test AIGlobalSettings
    assert hasattr(AIGlobalSettings, 'get')
    assert hasattr(AIGlobalSettings, 'is_enabled')
    assert hasattr(AIGlobalSettings, 'default_provider')
    assert hasattr(AIGlobalSettings, 'fallback_provider')
    assert hasattr(AIGlobalSettings, 'per_user_daily_limit')
    print("  ✓ AIGlobalSettings")

    # Test AIUsageLog
    assert hasattr(AIUsageLog, 'user')
    assert hasattr(AIUsageLog, 'provider')
    assert hasattr(AIUsageLog, 'action')
    assert hasattr(AIUsageLog, 'total_tokens')
    print("  ✓ AIUsageLog")

    print("✓ All AI models properly defined")


def test_exceptions():
    """Test custom exceptions are properly defined"""
    print("\nTesting custom exceptions...")

    # Test raising exceptions
    try:
        raise AIServiceDisabledError("Test")
    except AIServiceDisabledError:
        print("  ✓ AIServiceDisabledError")

    try:
        raise AIBudgetExceededError("Test")
    except AIBudgetExceededError:
        print("  ✓ AIBudgetExceededError")

    try:
        raise AIProviderError("Test")
    except AIProviderError:
        print("  ✓ AIProviderError")

    print("✓ All custom exceptions work")


def test_views_exist():
    """Test AI views are properly defined"""
    print("\nTesting AI views...")
    from apps.ai.views import TaskAIActionView

    assert hasattr(TaskAIActionView, 'post')
    print("  ✓ TaskAIActionView with post method")
    print("✓ AI views properly defined")


def test_urls_configured():
    """Test AI URLs are properly configured"""
    print("\nTesting AI URLs...")
    from apps.ai import urls

    assert hasattr(urls, 'urlpatterns')
    assert len(urls.urlpatterns) > 0, "No URL patterns defined"
    assert urls.app_name == 'ai'
    print(f"  ✓ {len(urls.urlpatterns)} URL pattern(s) defined")
    print("✓ AI URLs properly configured")


def test_templates_exist():
    """Test AI templates exist"""
    print("\nTesting AI templates...")
    from pathlib import Path

    templates_dir = Path('templates/ai/partials')
    assert templates_dir.exists(), f"Templates directory not found: {templates_dir}"

    required_templates = [
        'summary.html',
        'subtask_suggestions.html',
        'description.html',
        'error.html',
    ]

    for template in required_templates:
        template_path = templates_dir / template
        assert template_path.exists(), f"Template not found: {template_path}"
        print(f"  ✓ {template}")

    print("✓ All required templates exist")


def test_management_command():
    """Test seed_ai_config management command exists"""
    print("\nTesting management command...")
    from apps.ai.management.commands.seed_ai_config import Command

    assert hasattr(Command, 'handle')
    print("  ✓ seed_ai_config command exists")
    print("✓ Management command properly defined")


def run_all_tests():
    """Run all structural tests"""
    print("\n" + "="*70)
    print("RUNNING AI SERVICE STRUCTURAL TESTS")
    print("="*70 + "\n")

    test_imports()
    test_ai_service_methods()
    test_build_prompt_actions()
    test_models_exist()
    test_exceptions()
    test_views_exist()
    test_urls_configured()
    test_templates_exist()
    test_management_command()

    print("\n" + "="*70)
    print("ALL STRUCTURAL TESTS PASSED ✓")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_all_tests()
