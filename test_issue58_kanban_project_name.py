#!/usr/bin/env python
"""
Test script to verify ISSUE-58: Display project name on Kanban cards.

This script tests:
- Project name appears on each Kanban card
- Color dot before project name matches project.color
- Long project names are truncated with text-overflow: ellipsis
- Works in both light and dark mode (uses CSS variables)
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.projects.models import Project, ProjectUserMembership
from apps.tasks.models import Task
from django.template.loader import render_to_string

User = get_user_model()


def setup_test_data():
    """Create test user, project with color, and task"""
    print("\n── Setting up test data ──")

    # Clean up existing test data
    Task.objects.filter(title='Test Task for Project Name Display').delete()
    Project.objects.filter(name__in=['Test Project Alpha', 'Test Project with a Very Long Name That Should Be Truncated']).delete()
    User.objects.filter(username='testuser_issue58').delete()

    # Create user
    user = User.objects.create_user(
        username='testuser_issue58',
        email='test58@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User58'
    )

    # Create project with a specific color
    project = Project.objects.create(
        name='Test Project Alpha',
        visibility='members',
        owner=user,
        color='#3b82f6'  # Blue color
    )
    ProjectUserMembership.objects.create(
        project=project,
        user=user,
        role='manager'
    )

    # Create project with very long name
    long_project = Project.objects.create(
        name='Test Project with a Very Long Name That Should Be Truncated',
        visibility='members',
        owner=user,
        color='#10b981'  # Green color
    )
    ProjectUserMembership.objects.create(
        project=long_project,
        user=user,
        role='manager'
    )

    # Create tasks
    task1 = Task.objects.create(
        title='Test Task for Project Name Display',
        project=project,
        status=Task.STATUS_TODO,
        created_by=user
    )

    task2 = Task.objects.create(
        title='Test Task with Long Project Name',
        project=long_project,
        status=Task.STATUS_TODO,
        created_by=user
    )

    print(f"✓ Created user: {user.username}")
    print(f"✓ Created project: {project.name} with color: {project.color}")
    print(f"✓ Created long-name project: {long_project.name}")
    print(f"✓ Created {Task.objects.filter(title__startswith='Test Task').count()} test tasks")

    return user, project, long_project, task1, task2


def test_project_name_in_kanban_board():
    """Test that project name appears on Kanban board cards"""
    client = Client()
    user = User.objects.get(username='testuser_issue58')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check that project name appears
    assert 'Test Project Alpha' in content, "Project name not found on Kanban board"

    print("✓ Project name appears on Kanban board")


def test_project_color_dot():
    """Test that colored dot matches project color"""
    user = User.objects.get(username='testuser_issue58')
    task = Task.objects.get(title='Test Task for Project Name Display')

    # Render the card template
    html = render_to_string('tasks/partials/card.html', {'task': task})

    # Check for colored dot with project color
    assert 'rounded-circle' in html, "Colored dot element not found"
    assert task.project.color in html, f"Project color {task.project.color} not found in card HTML"
    assert 'width:8px; height:8px' in html, "Dot size styles not found"

    print("✓ Colored dot with project color is present")


def test_project_name_display():
    """Test that project name is displayed with correct styling"""
    user = User.objects.get(username='testuser_issue58')
    task = Task.objects.get(title='Test Task for Project Name Display')

    # Render the card template
    html = render_to_string('tasks/partials/card.html', {'task': task})

    # Check for project name
    assert 'Test Project Alpha' in html, "Project name not in rendered card"

    # Check for styling attributes
    assert 'font-size:11px' in html, "Font size not set for project name"
    assert 'var(--friday-text-muted)' in html, "CSS variable for text color not used"
    assert 'white-space:nowrap' in html, "white-space:nowrap not set"
    assert 'text-overflow:ellipsis' in html, "text-overflow:ellipsis not set"
    assert 'max-width:180px' in html, "max-width not set for project name"

    print("✓ Project name has correct styling for ellipsis truncation")


def test_long_project_name_truncation():
    """Test that long project names can be truncated (max-width set)"""
    user = User.objects.get(username='testuser_issue58')
    task = Task.objects.get(title='Test Task with Long Project Name')

    # Render the card template
    html = render_to_string('tasks/partials/card.html', {'task': task})

    # Check that long project name is present
    assert 'Test Project with a Very Long Name That Should Be Truncated' in html, "Long project name not in rendered card"

    # Check that truncation styles are applied
    assert 'text-overflow:ellipsis' in html, "text-overflow:ellipsis not applied to long project name"
    assert 'overflow:hidden' in html, "overflow:hidden not applied"

    print("✓ Long project names have truncation styles applied")


def test_css_variables_for_dark_mode():
    """Test that CSS variables are used for color (works in light and dark mode)"""
    user = User.objects.get(username='testuser_issue58')
    task = Task.objects.get(title='Test Task for Project Name Display')

    # Render the card template
    html = render_to_string('tasks/partials/card.html', {'task': task})

    # Check that CSS variable is used for text color
    assert 'var(--friday-text-muted)' in html, "CSS variable not used for text color"

    print("✓ CSS variables used for theming (supports light and dark mode)")


def test_project_name_position():
    """Test that project name appears before meta-info section"""
    user = User.objects.get(username='testuser_issue58')
    task = Task.objects.get(title='Test Task for Project Name Display')

    # Render the card template
    html = render_to_string('tasks/partials/card.html', {'task': task})

    # Find position of project name and meta-info indicators
    project_name_pos = html.find('Test Project Alpha')

    # Look for meta-info indicators that should come after project name
    # These are common indicators in the meta-info section
    indicators = ['bi-hourglass-split', 'bi-list-task', 'bi-chat', 'bi-paperclip', 'bi-calendar']

    # Find the first meta-info indicator
    meta_info_pos = float('inf')
    for indicator in indicators:
        pos = html.find(indicator)
        if pos != -1 and pos < meta_info_pos:
            meta_info_pos = pos

    # If we found both, project name should come before meta-info
    if project_name_pos != -1 and meta_info_pos != float('inf'):
        assert project_name_pos < meta_info_pos, "Project name should appear before meta-info section"

    print("✓ Project name positioned correctly (before meta-info)")


def run_all_tests():
    """Run all test functions"""
    print("\n" + "="*60)
    print("ISSUE-58: Kanban Project Name Display - Acceptance Tests")
    print("="*60)

    # Setup test data
    setup_test_data()

    # Run tests
    tests = [
        test_project_name_in_kanban_board,
        test_project_color_dot,
        test_project_name_display,
        test_long_project_name_truncation,
        test_css_variables_for_dark_mode,
        test_project_name_position,
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
        print("\n✓ All acceptance criteria tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
