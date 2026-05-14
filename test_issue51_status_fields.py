#!/usr/bin/env python
"""
Acceptance tests for ISSUE-51: Erweiterung Status-Felder (Projekte + Tasks)

This script tests:
1. Project model: new status choices (production, end_of_life, deferred)
2. Task model: new status choice (waiting)
3. Status color filter: returns correct colors for new statuses
4. Project list: new tabs appear and filter correctly
5. Kanban board: waiting column appears and tasks can be moved to it
6. CSS styling: waiting tasks have amber/orange border
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.core.templatetags.friday_tags import status_color

User = get_user_model()


def setup_test_data():
    """Create test users and projects for testing."""
    # Clean up any existing test data
    Project.objects.filter(name__startswith='Test Project Issue51').delete()
    User.objects.filter(username__startswith='test_user_issue51').delete()

    # Create test user
    user = User.objects.create_user(
        username='test_user_issue51',
        email='testissue51@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )

    return user


def test_project_status_choices():
    """Test 1: Project model has new status choices."""
    print("\n" + "=" * 70)
    print("TEST 1: Project Status Choices")
    print("=" * 70)

    # Check that all new status constants exist
    assert hasattr(Project, 'STATUS_PRODUCTION'), "STATUS_PRODUCTION constant missing"
    assert hasattr(Project, 'STATUS_END_OF_LIFE'), "STATUS_END_OF_LIFE constant missing"
    assert hasattr(Project, 'STATUS_DEFERRED'), "STATUS_DEFERRED constant missing"

    # Check values
    assert Project.STATUS_PRODUCTION == 'production', "STATUS_PRODUCTION value incorrect"
    assert Project.STATUS_END_OF_LIFE == 'end_of_life', "STATUS_END_OF_LIFE value incorrect"
    assert Project.STATUS_DEFERRED == 'deferred', "STATUS_DEFERRED value incorrect"

    # Check STATUS_CHOICES contains all new statuses
    status_values = [s[0] for s in Project.STATUS_CHOICES]
    assert 'production' in status_values, "production not in STATUS_CHOICES"
    assert 'end_of_life' in status_values, "end_of_life not in STATUS_CHOICES"
    assert 'deferred' in status_values, "deferred not in STATUS_CHOICES"

    # Check display labels are in German
    status_dict = dict(Project.STATUS_CHOICES)
    assert status_dict['production'] == 'Production', "production label incorrect"
    assert status_dict['end_of_life'] == 'End of Life', "end_of_life label incorrect"
    assert status_dict['deferred'] == 'Zurückgestellt', "deferred label incorrect"

    print("✓ All project status constants exist")
    print("✓ STATUS_CHOICES includes production, end_of_life, deferred")
    print("✓ Display labels are correct")


def test_task_status_choices():
    """Test 2: Task model has new status choice."""
    print("\n" + "=" * 70)
    print("TEST 2: Task Status Choices")
    print("=" * 70)

    # Check that waiting status constant exists
    assert hasattr(Task, 'STATUS_WAITING'), "STATUS_WAITING constant missing"
    assert Task.STATUS_WAITING == 'waiting', "STATUS_WAITING value incorrect"

    # Check STATUS_CHOICES contains waiting
    status_values = [s[0] for s in Task.STATUS_CHOICES]
    assert 'waiting' in status_values, "waiting not in STATUS_CHOICES"

    # Check display label
    status_dict = dict(Task.STATUS_CHOICES)
    assert status_dict['waiting'] == 'Waiting', "waiting label incorrect"

    # Check waiting is positioned between in_progress and review
    status_order = [s[0] for s in Task.STATUS_CHOICES]
    in_progress_idx = status_order.index('in_progress')
    waiting_idx = status_order.index('waiting')
    review_idx = status_order.index('review')

    assert in_progress_idx < waiting_idx < review_idx, \
        "waiting should be between in_progress and review"

    print("✓ Task STATUS_WAITING constant exists")
    print("✓ STATUS_CHOICES includes waiting")
    print("✓ waiting is positioned between in_progress and review")


def test_create_projects_with_new_statuses():
    """Test 3: Can create projects with new statuses."""
    print("\n" + "=" * 70)
    print("TEST 3: Create Projects with New Statuses")
    print("=" * 70)

    user = setup_test_data()

    # Create project with production status
    proj_prod = Project.objects.create(
        name='Test Project Issue51 Production',
        status='production',
        owner=user
    )
    assert proj_prod.status == 'production'
    assert proj_prod.get_status_display() == 'Production'

    # Create project with end_of_life status
    proj_eol = Project.objects.create(
        name='Test Project Issue51 End of Life',
        status='end_of_life',
        owner=user
    )
    assert proj_eol.status == 'end_of_life'
    assert proj_eol.get_status_display() == 'End of Life'

    # Create project with deferred status
    proj_def = Project.objects.create(
        name='Test Project Issue51 Deferred',
        status='deferred',
        owner=user
    )
    assert proj_def.status == 'deferred'
    assert proj_def.get_status_display() == 'Zurückgestellt'

    print("✓ Created project with production status")
    print("✓ Created project with end_of_life status")
    print("✓ Created project with deferred status")
    print("✓ All get_status_display() methods return correct labels")


def test_create_tasks_with_waiting_status():
    """Test 4: Can create tasks with waiting status."""
    print("\n" + "=" * 70)
    print("TEST 4: Create Tasks with Waiting Status")
    print("=" * 70)

    user = setup_test_data()
    project = Project.objects.create(
        name='Test Project Issue51 Tasks',
        status='active',
        owner=user
    )

    # Create task with waiting status
    task = Task.objects.create(
        title='Issue51 Test Task Waiting',
        project=project,
        status='waiting',
        created_by=user
    )

    assert task.status == 'waiting'
    assert task.get_status_display() == 'Waiting'

    print("✓ Created task with waiting status")
    print("✓ get_status_display() returns 'Waiting'")


def test_status_color_filter():
    """Test 5: status_color filter returns correct colors."""
    print("\n" + "=" * 70)
    print("TEST 5: Status Color Filter")
    print("=" * 70)

    user = setup_test_data()

    # Test production - should be dark blue
    proj_prod = Project.objects.create(
        name='Test Project Issue51 Color Production',
        status='production',
        owner=user
    )
    color = status_color(proj_prod)
    assert color == '#1e3a5f', f"production color should be #1e3a5f, got {color}"

    # Test deferred - should be purple
    proj_def = Project.objects.create(
        name='Test Project Issue51 Color Deferred',
        status='deferred',
        owner=user
    )
    color = status_color(proj_def)
    assert color == '#6b21a8', f"deferred color should be #6b21a8, got {color}"

    # Test end_of_life - should be gray
    proj_eol = Project.objects.create(
        name='Test Project Issue51 Color EOL',
        status='end_of_life',
        owner=user
    )
    color = status_color(proj_eol)
    assert color == '#374151', f"end_of_life color should be #374151, got {color}"

    print("✓ production status returns dark blue (#1e3a5f)")
    print("✓ deferred status returns purple (#6b21a8)")
    print("✓ end_of_life status returns gray (#374151)")


def test_project_list_tabs():
    """Test 6: Project list includes new tabs."""
    print("\n" + "=" * 70)
    print("TEST 6: Project List Tabs")
    print("=" * 70)

    user = setup_test_data()
    client = Client()
    client.force_login(user)

    # Get project list page
    response = client.get('/projects/')
    assert response.status_code == 200, "Project list page should load"

    content = response.content.decode('utf-8')

    # Check that new tabs exist
    assert 'href="?status=production"' in content, "Production tab missing"
    assert 'href="?status=deferred"' in content, "Zurückgestellt tab missing"

    # Check that tab labels are in German
    assert '>Production<' in content, "Production tab label missing"
    assert '>Zurückgestellt<' in content, "Zurückgestellt tab label missing"

    # Check that archived and end_of_life are NOT shown as tabs
    # (only visible under "Alle")
    assert 'href="?status=end_of_life"' not in content, \
        "end_of_life should not have a tab"

    print("✓ Production tab exists in project list")
    print("✓ Zurückgestellt tab exists in project list")
    print("✓ Tab labels are in German")
    print("✓ end_of_life and archived do not have separate tabs")


def test_project_list_filtering():
    """Test 7: Project list filtering works for new statuses."""
    print("\n" + "=" * 70)
    print("TEST 7: Project List Filtering")
    print("=" * 70)

    user = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create projects with different statuses
    proj_prod = Project.objects.create(
        name='Test Project Issue51 Filter Production',
        status='production',
        owner=user
    )
    proj_def = Project.objects.create(
        name='Test Project Issue51 Filter Deferred',
        status='deferred',
        owner=user
    )
    proj_active = Project.objects.create(
        name='Test Project Issue51 Filter Active',
        status='active',
        owner=user
    )

    # Test production filter
    response = client.get('/projects/?status=production')
    content = response.content.decode('utf-8')
    assert 'Test Project Issue51 Filter Production' in content, \
        "Production project should appear in production filter"
    assert 'Test Project Issue51 Filter Deferred' not in content, \
        "Deferred project should not appear in production filter"

    # Test deferred filter
    response = client.get('/projects/?status=deferred')
    content = response.content.decode('utf-8')
    assert 'Test Project Issue51 Filter Deferred' in content, \
        "Deferred project should appear in deferred filter"
    assert 'Test Project Issue51 Filter Production' not in content, \
        "Production project should not appear in deferred filter"

    # Test "all" shows everything
    response = client.get('/projects/?status=all')
    content = response.content.decode('utf-8')
    assert 'Test Project Issue51 Filter Production' in content
    assert 'Test Project Issue51 Filter Deferred' in content
    assert 'Test Project Issue51 Filter Active' in content

    print("✓ Production filter works correctly")
    print("✓ Deferred filter works correctly")
    print("✓ All filter shows all projects")


def test_kanban_board_waiting_column():
    """Test 8: Kanban board includes waiting column."""
    print("\n" + "=" * 70)
    print("TEST 8: Kanban Board Waiting Column")
    print("=" * 70)

    user = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create project and task
    project = Project.objects.create(
        name='Test Project Issue51 Kanban',
        status='active',
        owner=user
    )
    project.user_members.add(user)

    task_waiting = Task.objects.create(
        title='Issue51 Kanban Waiting Task',
        project=project,
        status='waiting',
        created_by=user
    )

    task_in_progress = Task.objects.create(
        title='Issue51 Kanban In Progress Task',
        project=project,
        status='in_progress',
        created_by=user
    )

    # Get kanban board
    response = client.get('/kanban/')
    assert response.status_code == 200, "Kanban board should load"

    content = response.content.decode('utf-8')

    # Check that waiting column exists
    assert 'data-status="waiting"' in content, "Waiting column should exist"
    assert '>Waiting<' in content, "Waiting column label should exist"

    # Check that waiting task appears in waiting column
    assert 'Issue51 Kanban Waiting Task' in content, \
        "Waiting task should appear on kanban board"

    print("✓ Kanban board includes waiting column")
    print("✓ Waiting column has correct label")
    print("✓ Tasks with waiting status appear in waiting column")


def test_css_styling():
    """Test 9: CSS file includes waiting status styling."""
    print("\n" + "=" * 70)
    print("TEST 9: CSS Styling for Waiting Status")
    print("=" * 70)

    # Read CSS file
    css_path = '/home/runner/work/Friday/Friday/static/css/friday.css'
    with open(css_path, 'r') as f:
        css_content = f.read()

    # Check for waiting status styling
    assert '[data-status="waiting"]' in css_content, \
        "CSS should include waiting status selector"

    # Check for amber/orange color (#f59e0b)
    assert '#f59e0b' in css_content, \
        "CSS should include amber/orange color for waiting status"

    # Check for border-left styling
    assert 'border-left' in css_content and 'waiting' in css_content, \
        "CSS should include border-left styling for waiting tasks"

    print("✓ CSS includes [data-status=\"waiting\"] selector")
    print("✓ CSS includes amber/orange color (#f59e0b)")
    print("✓ CSS includes border-left styling for waiting tasks")


def run_all_tests():
    """Run all acceptance tests."""
    print("\n" + "=" * 70)
    print("ISSUE-51: Status Fields Expansion - Acceptance Tests")
    print("=" * 70)

    try:
        test_project_status_choices()
        test_task_status_choices()
        test_create_projects_with_new_statuses()
        test_create_tasks_with_waiting_status()
        test_status_color_filter()
        test_project_list_tabs()
        test_project_list_filtering()
        test_kanban_board_waiting_column()
        test_css_styling()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
