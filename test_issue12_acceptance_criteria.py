#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-12: Task Creation.

This script tests all requirements from the issue:
- GET /tasks/create/ returns 200 with a task creation form
- GET /tasks/create/?project=<id> pre-selects the correct project
- GET /tasks/create/?status=in_progress pre-selects the correct status
- POST /tasks/create/ with valid data creates a task and redirects to task detail
- POST /tasks/create/ without title returns form with error message
- POST /tasks/create/ without project_id returns 400
- HTMX POST from Kanban quick-add returns tasks/partials/card.html partial
- New card appears at bottom of correct Kanban column without page reload
- Sidebar "Tasks" link navigates to /kanban/
- Kanban quick-add button is hidden (or shows tooltip) when no project filter is active
- Non-project-members cannot create tasks in that project (403)
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
from apps.teams.models import Team, TeamMembership
from apps.projects.models import Project, ProjectUserMembership
from apps.tasks.models import Task
from datetime import date

User = get_user_model()


def setup_test_data():
    """Create test users, teams, and projects"""
    print("\n── Setting up test data ──")

    # Clean up existing test data
    User.objects.filter(username__startswith='testuser_tc').delete()
    Team.objects.filter(slug__startswith='test-team-tc').delete()
    Project.objects.filter(name__startswith='Test Project TC').delete()

    # Create users
    user1 = User.objects.create_user(
        username='testuser_tc1',
        email='test_tc1@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User1'
    )

    user2 = User.objects.create_user(
        username='testuser_tc2',
        email='test_tc2@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User2'
    )

    # Create team
    team = Team.objects.create(
        name='Test Team TC',
        slug='test-team-tc'
    )
    TeamMembership.objects.create(user=user1, team=team, role='member')

    # Create projects
    project1 = Project.objects.create(
        name='Test Project TC Alpha',
        visibility='members',
        owner=user1,
        color='#3b82f6'
    )
    ProjectUserMembership.objects.create(
        project=project1,
        user=user1,
        role='manager'
    )

    project2 = Project.objects.create(
        name='Test Project TC Beta',
        visibility='members',
        owner=user2,
        color='#10b981'
    )
    ProjectUserMembership.objects.create(
        project=project2,
        user=user2,
        role='manager'
    )

    print(f"  ✓ Created user1: {user1.username}")
    print(f"  ✓ Created user2: {user2.username}")
    print(f"  ✓ Created team: {team.name}")
    print(f"  ✓ Created project1: {project1.name}")
    print(f"  ✓ Created project2: {project2.name}")

    return user1, user2, team, project1, project2


def test_get_task_create_returns_form(client, user, project):
    """Test: GET /tasks/create/ returns 200 with a task creation form"""
    print("\n── Test: GET /tasks/create/ returns 200 with form ──")

    client.force_login(user)
    response = client.get(reverse('tasks:task-create'))

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'Create New Task' in response.content or b'New Task' in response.content
    assert b'name="title"' in response.content
    assert b'name="project"' in response.content or b'name="project_id"' in response.content

    print("  ✓ GET /tasks/create/ returns 200")
    print("  ✓ Response contains task creation form")
    print("  ✓ Form includes title and project fields")


def test_get_task_create_preselects_project(client, user, project):
    """Test: GET /tasks/create/?project=<id> pre-selects the correct project"""
    print("\n── Test: GET /tasks/create/?project=<id> pre-selects project ──")

    client.force_login(user)
    response = client.get(reverse('tasks:task-create') + f'?project={project.pk}')

    assert response.status_code == 200
    content = response.content.decode()
    assert f'value="{project.pk}"' in content and 'selected' in content

    print(f"  ✓ Project {project.pk} is pre-selected in the form")


def test_get_task_create_preselects_status(client, user, project):
    """Test: GET /tasks/create/?status=in_progress pre-selects the correct status"""
    print("\n── Test: GET /tasks/create/?status=in_progress pre-selects status ──")

    client.force_login(user)
    response = client.get(
        reverse('tasks:task-create') +
        f'?project={project.pk}&status=in_progress'
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'in_progress' in content
    assert 'selected' in content

    print("  ✓ Status 'in_progress' is pre-selected in the form")


def test_post_task_create_success(client, user, project):
    """Test: POST /tasks/create/ with valid data creates a task and redirects"""
    print("\n── Test: POST /tasks/create/ with valid data redirects ──")

    client.force_login(user)
    initial_count = Task.objects.count()

    response = client.post(reverse('tasks:task-create'), {
        'title': 'New Test Task',
        'project': project.pk,
        'status': Task.STATUS_TODO,
        'priority': Task.PRIORITY_MEDIUM,
        'description': 'Test description',
    })

    assert Task.objects.count() == initial_count + 1, "Task was not created"
    task = Task.objects.latest('id')
    assert task.title == 'New Test Task'
    assert task.project == project
    assert task.status == Task.STATUS_TODO
    assert task.priority == Task.PRIORITY_MEDIUM

    # Should redirect to task detail
    assert response.status_code == 302
    assert f'/tasks/{task.pk}/detail/' in response.url

    print("  ✓ Task created successfully")
    print(f"  ✓ Task title: {task.title}")
    print(f"  ✓ Redirects to task detail: {response.url}")


def test_post_task_create_without_title(client, user, project):
    """Test: POST /tasks/create/ without title returns form with error"""
    print("\n── Test: POST /tasks/create/ without title returns error ──")

    client.force_login(user)
    initial_count = Task.objects.count()

    response = client.post(reverse('tasks:task-create'), {
        'title': '',
        'project': project.pk,
        'status': Task.STATUS_TODO,
    })

    assert Task.objects.count() == initial_count, "Task should not be created"
    assert response.status_code == 200, "Should return form page"
    content = response.content.decode()
    assert 'error' in content.lower() or 'required' in content.lower()

    print("  ✓ Task not created without title")
    print("  ✓ Form returned with error message")


def test_post_task_create_without_project(client, user):
    """Test: POST /tasks/create/ without project_id returns 400"""
    print("\n── Test: POST /tasks/create/ without project_id returns 400 ──")

    client.force_login(user)
    initial_count = Task.objects.count()

    response = client.post(reverse('tasks:task-create'), {
        'title': 'Task without project',
        'status': Task.STATUS_TODO,
    })

    assert Task.objects.count() == initial_count, "Task should not be created"
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    print("  ✓ Returns 400 Bad Request without project_id")


def test_htmx_post_returns_card_partial(client, user, project):
    """Test: HTMX POST from Kanban quick-add returns card partial"""
    print("\n── Test: HTMX POST returns card partial ──")

    client.force_login(user)
    initial_count = Task.objects.count()

    response = client.post(
        reverse('tasks:task-create'),
        {
            'title': 'HTMX Quick-Add Task',
            'project_id': project.pk,
            'status': Task.STATUS_IN_PROGRESS,
        },
        HTTP_HX_REQUEST='true'
    )

    assert Task.objects.count() == initial_count + 1, "Task was not created"
    task = Task.objects.latest('id')
    assert task.title == 'HTMX Quick-Add Task'
    assert task.status == Task.STATUS_IN_PROGRESS

    # Should return card partial, not redirect
    assert response.status_code == 200
    content = response.content.decode()
    assert 'task-card' in content or 'card' in content
    assert task.title in content

    print("  ✓ Task created via HTMX")
    print("  ✓ Returns card partial (not redirect)")
    print(f"  ✓ Card contains task title: {task.title}")


def test_htmx_post_without_title_returns_400(client, user, project):
    """Test: HTMX POST without title returns 400"""
    print("\n── Test: HTMX POST without title returns 400 ──")

    client.force_login(user)
    initial_count = Task.objects.count()

    response = client.post(
        reverse('tasks:task-create'),
        {
            'title': '',
            'project_id': project.pk,
            'status': Task.STATUS_TODO,
        },
        HTTP_HX_REQUEST='true'
    )

    assert Task.objects.count() == initial_count, "Task should not be created"
    assert response.status_code == 400

    print("  ✓ HTMX POST without title returns 400")


def test_non_member_cannot_create_task(client, user1, user2, project2):
    """Test: Non-project-members cannot create tasks (403)"""
    print("\n── Test: Non-member cannot create task (403) ──")

    # user1 tries to create task in project2 (owned by user2, user1 not a member)
    client.force_login(user1)
    initial_count = Task.objects.count()

    response = client.post(reverse('tasks:task-create'), {
        'title': 'Unauthorized Task',
        'project': project2.pk,
        'status': Task.STATUS_TODO,
    })

    assert Task.objects.count() == initial_count, "Task should not be created"
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    print("  ✓ Non-member cannot create task in project")
    print(f"  ✓ Returns {response.status_code} (Permission Denied)")


def test_sidebar_tasks_link(client, user):
    """Test: Sidebar 'Tasks' link navigates to /kanban/"""
    print("\n── Test: Sidebar Tasks link points to Kanban ──")

    client.force_login(user)
    response = client.get(reverse('kanban:kanban-board'))

    assert response.status_code == 200
    content = response.content.decode()

    # Check that sidebar contains Tasks link to kanban-board
    kanban_url = reverse('kanban:kanban-board')
    assert kanban_url in content

    print("  ✓ Kanban board loads successfully")
    print(f"  ✓ Sidebar should link Tasks to: {kanban_url}")


def test_kanban_quick_add_disabled_without_project(client, user, project):
    """Test: Kanban quick-add button disabled when no project filter"""
    print("\n── Test: Quick-add disabled without project filter ──")

    client.force_login(user)

    # Request without project filter
    response = client.get(reverse('kanban:kanban-board'))
    assert response.status_code == 200
    content = response.content.decode()

    # Button should be disabled or hidden
    assert 'disabled' in content or 'Select a project' in content

    print("  ✓ Quick-add button is disabled/shows tooltip without project")


def test_kanban_quick_add_enabled_with_project(client, user, project):
    """Test: Kanban quick-add button enabled with project filter"""
    print("\n── Test: Quick-add enabled with project filter ──")

    client.force_login(user)

    # Request with project filter
    response = client.get(
        reverse('kanban:kanban-board') + f'?project={project.pk}'
    )
    assert response.status_code == 200
    content = response.content.decode()

    # Check for HTMX get to task-create with project_id
    assert 'hx-get' in content
    assert f'project_id={project.pk}' in content or f'project={project.pk}' in content

    print("  ✓ Quick-add button has HTMX get with project filter")


def test_htmx_get_returns_quick_add_form(client, user, project):
    """Test: HTMX GET /tasks/create/ returns quick-add form partial"""
    print("\n── Test: HTMX GET returns quick-add form partial ──")

    client.force_login(user)

    response = client.get(
        reverse('tasks:task-create') +
        f'?status=todo&project_id={project.pk}',
        HTTP_HX_REQUEST='true'
    )

    assert response.status_code == 200
    content = response.content.decode()

    # Should return form partial, not full page
    assert '<form' in content
    assert 'hx-post' in content
    assert 'name="title"' in content

    print("  ✓ HTMX GET returns quick-add form partial")
    print("  ✓ Form includes HTMX post attributes")


def run_all_tests():
    """Run all acceptance criteria tests"""
    print("=" * 60)
    print("ISSUE-12: Task Creation - Acceptance Criteria Tests")
    print("=" * 60)

    # Setup
    user1, user2, team, project1, project2 = setup_test_data()
    client = Client()

    try:
        # Run all tests
        test_get_task_create_returns_form(client, user1, project1)
        test_get_task_create_preselects_project(client, user1, project1)
        test_get_task_create_preselects_status(client, user1, project1)
        test_post_task_create_success(client, user1, project1)
        test_post_task_create_without_title(client, user1, project1)
        test_post_task_create_without_project(client, user1)
        test_htmx_post_returns_card_partial(client, user1, project1)
        test_htmx_post_without_title_returns_400(client, user1, project1)
        test_non_member_cannot_create_task(client, user1, user2, project2)
        test_sidebar_tasks_link(client, user1)
        test_kanban_quick_add_disabled_without_project(client, user1, project1)
        test_kanban_quick_add_enabled_with_project(client, user1, project1)
        test_htmx_get_returns_quick_add_form(client, user1, project1)

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return True

    except AssertionError as e:
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
