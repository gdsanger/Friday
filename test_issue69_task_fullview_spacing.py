#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-69.

This script tests:
- Task full-view has proper section wrappers with CSS classes
- Sections have proper spacing (16px margin-bottom)
- Accordion items have borders and rounded corners
- Two-column layout uses grid structure
- Sidebar has sticky positioning
"""

import os
import sys
import django

# Setup Django with SQLite for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ['DATABASE_URL'] = 'sqlite:///test_db.sqlite3'
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.tasks.models import Task, TaskComment
from apps.projects.models import Project, ProjectUserMembership
from apps.core.models import Organisation

User = get_user_model()


def setup_test_data():
    """Create test user, project, and task."""
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser69',
        defaults={
            'email': 'test69@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()

    # Create organisation
    org, _ = Organisation.objects.get_or_create(
        name='Test Org',
        defaults={'slug': 'test-org'}
    )

    # Create test project
    project, created = Project.objects.get_or_create(
        name='Test Project ISSUE-69',
        defaults={
            'description': 'Test project for ISSUE-69',
            'owner': user,
            'organisation': org,
        }
    )

    # Add user as project member
    ProjectUserMembership.objects.get_or_create(
        project=project,
        user=user,
        defaults={'role': 'manager'}
    )

    # Create test task
    task, created = Task.objects.get_or_create(
        title='Test Task for ISSUE-69',
        project=project,
        defaults={
            'description': 'Testing spacing and visual separation',
            'status': Task.STATUS_TODO,
            'created_by': user,
            'requester': user,
        }
    )

    return user, project, task


def test_task_full_view_layout():
    """Test that task full view has the two-column grid layout."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail-full', args=[task.pk])
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    content = response.content.decode('utf-8')

    # Check for task-full-layout class
    assert 'task-full-layout' in content, "task-full-layout class not found"
    print("✓ Task full view uses task-full-layout grid structure")

    # Check for sticky sidebar
    assert 'task-full-sidebar' in content, "task-full-sidebar class not found"
    print("✓ Sidebar has task-full-sidebar class for sticky positioning")


def test_tabs_section_wrapper():
    """Test that tabs section has proper card wrapper."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail-full', args=[task.pk])
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    content = response.content.decode('utf-8')

    # Check for task-tabs-section class
    assert 'task-tabs-section' in content, "task-tabs-section class not found"
    print("✓ Tabs section has task-tabs-section wrapper")


def test_activity_section_wrapper():
    """Test that activity section has proper wrapper."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail-full', args=[task.pk])
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    content = response.content.decode('utf-8')

    # Check for activity-section class
    assert 'activity-section' in content, "activity-section class not found"
    print("✓ Activity section has activity-section wrapper")


def test_accordion_items_structure():
    """Test that accordion items don't have old inline border styles."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail-full', args=[task.pk])
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    content = response.content.decode('utf-8')

    # Check that old border-0 border-top classes are removed
    # The accordion-item should not have inline border-0 class
    assert 'accordion-item border-0 border-top' not in content, \
        "Old inline border classes still present in accordion items"
    print("✓ Accordion items have been updated to use CSS styling")

    # Check for accordion structure
    assert 'id="taskAccordion"' in content, "taskAccordion not found"
    assert 'accordion-item' in content, "accordion-item class not found"
    print("✓ Accordion structure is present")


def test_css_classes_exist():
    """Test that the CSS file contains the new styling classes."""
    css_path = '/home/runner/work/Friday/Friday/static/css/friday.css'

    with open(css_path, 'r') as f:
        css_content = f.read()

    # Check for key CSS classes
    assert '.task-section' in css_content, "task-section class not found in CSS"
    assert '.task-tabs-section' in css_content, "task-tabs-section class not found in CSS"
    assert '.activity-section' in css_content, "activity-section class not found in CSS"
    assert '.task-full-layout' in css_content, "task-full-layout class not found in CSS"
    assert '.task-full-sidebar' in css_content, "task-full-sidebar class not found in CSS"
    assert '.task-meta-section' in css_content, "task-meta-section class not found in CSS"

    print("✓ All required CSS classes exist in friday.css")

    # Check for spacing values
    assert 'margin-bottom: 16px' in css_content, "16px margin-bottom not found"
    assert 'border-radius: 10px' in css_content, "10px border-radius not found"
    print("✓ CSS includes proper spacing values (16px margins, 10px border-radius)")

    # Check for grid layout
    assert 'grid-template-columns: 1fr 340px' in css_content, "Grid columns not found"
    print("✓ CSS includes two-column grid layout")

    # Check for sticky positioning
    assert 'position: sticky' in css_content, "Sticky positioning not found"
    print("✓ CSS includes sticky sidebar positioning")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*60)
    print("ISSUE-69: Task Full-View Spacing & Visual Separation")
    print("="*60 + "\n")

    tests = [
        ("Task Full View Layout", test_task_full_view_layout),
        ("Tabs Section Wrapper", test_tabs_section_wrapper),
        ("Activity Section Wrapper", test_activity_section_wrapper),
        ("Accordion Items Structure", test_accordion_items_structure),
        ("CSS Classes Exist", test_css_classes_exist),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\nTest: {test_name}")
            print("-" * 60)
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
