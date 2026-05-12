#!/usr/bin/env python
"""
Structural test for Kanban app to verify proper configuration.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.urls import reverse, resolve
from django.conf import settings
from apps.kanban import views


def test_app_installed():
    """Test kanban app is in INSTALLED_APPS"""
    assert 'apps.kanban' in settings.INSTALLED_APPS, "kanban app not in INSTALLED_APPS"
    print("✓ Kanban app is installed")


def test_url_configuration():
    """Test URL routing is configured correctly"""
    # Test kanban board URL
    url = reverse('kanban:kanban-board')
    assert url == '/kanban/', f"Expected /kanban/, got {url}"

    # Test URL resolves to correct view
    resolved = resolve('/kanban/')
    assert resolved.func.view_class == views.KanbanBoardView, "URL doesn't resolve to KanbanBoardView"

    print("✓ URL configuration is correct")


def test_view_exists():
    """Test KanbanBoardView exists and is configured"""
    assert hasattr(views, 'KanbanBoardView'), "KanbanBoardView not found"
    assert hasattr(views.KanbanBoardView, 'get'), "KanbanBoardView doesn't have get method"
    print("✓ KanbanBoardView exists and is configured")


def test_templates_exist():
    """Test required templates exist"""
    from django.template.loader import get_template
    templates = [
        'kanban/board.html',
        'kanban/partials/board.html',
    ]
    for template_name in templates:
        try:
            get_template(template_name)
        except Exception as e:
            assert False, f"Template {template_name} not found: {e}"
    print("✓ All required templates exist")


def test_templatetags_exist():
    """Test custom templatetags are available"""
    from django.template import Template, Context
    template_code = "{% load kanban_tags %}{{ test_dict|get_item:'key' }}"
    template = Template(template_code)
    context = Context({'test_dict': {'key': 'value'}})
    result = template.render(context)
    assert result == 'value', "get_item template tag not working"
    print("✓ Custom templatetags work correctly")


def run_all_tests():
    """Run all structural tests"""
    print("\n" + "="*60)
    print("ISSUE-09: Kanban App - Structural Tests")
    print("="*60 + "\n")

    tests = [
        test_app_installed,
        test_url_configuration,
        test_view_exists,
        test_templates_exist,
        test_templatetags_exist,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error - {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60)

    if failed == 0:
        print("\n✓ All structural tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
