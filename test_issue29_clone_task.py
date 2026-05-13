#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-29: Task Clone Feature.

This script tests:
- POST /tasks/<pk>/clone/ creates a new task with [Kopie] prefix
- Clone has status 'backlog' regardless of original status
- Clone copies: title, description, priority, labels, assignee, due_date, deadline, estimated_h, client
- Clone does NOT copy: comments, attachments, time entries, watchers
- With include_subtasks=1: subtasks are cloned as children of the new task
- Clone button visible in slide-over and full detail view
- Non-members cannot clone tasks (403)
- After clone, user is redirected to the new task's detail page
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
from django.utils import timezone
from datetime import date, timedelta

from apps.projects.models import Project
from apps.tasks.models import Task, Label, Comment, Attachment, TimeEntry
from apps.teams.models import Team
from apps.core.models import Client as ClientModel

User = get_user_model()


def setup_test_data():
    """Create test users, projects, tasks, and related data."""
    # Clean up any existing test data first
    Task.objects.filter(title__contains='Issue29').delete()
    Project.objects.filter(name__startswith='Test Project Issue29').delete()
    User.objects.filter(username__startswith='test_').filter(username__contains='issue29').delete()
    Label.objects.filter(name__startswith='Issue29').delete()
    ClientModel.objects.filter(name__startswith='Test Client Issue29').delete()
    Team.objects.filter(slug__startswith='test-team-issue29').delete()

    # Create test users
    member_user = User.objects.create_user(
        username='test_member_issue29',
        email='member29@test.com',
        password='testpass123',
        display_name='Test Member Issue29'
    )

    non_member_user = User.objects.create_user(
        username='test_nonmember_issue29',
        email='nonmember29@test.com',
        password='testpass123',
        display_name='Test Non-Member Issue29'
    )

    assignee_user = User.objects.create_user(
        username='test_assignee_issue29',
        email='assignee29@test.com',
        password='testpass123',
        display_name='Test Assignee Issue29'
    )

    # Create test team
    team = Team.objects.create(
        name='Test Team Issue29',
        slug='test-team-issue29',
        description='Test team for issue 29',
        color='#6366f1',
        icon='people-fill'
    )

    # Create test client
    client = ClientModel.objects.create(
        name='Test Client Issue29',
        slug='test-client-issue29',
        short_name='TCI29',
        color='#f59e0b',
        is_active=True
    )

    # Create test project
    project = Project.objects.create(
        name='Test Project Issue29',
        description='Test project for issue 29',
        status='active',
        color='#2980b9',
        owner=member_user
    )
    project.user_members.add(member_user, assignee_user)

    # Create test labels
    label1 = Label.objects.create(name='Issue29 Label 1', color='#ef4444')
    label2 = Label.objects.create(name='Issue29 Label 2', color='#3b82f6')

    # Create test task with all fields populated
    original_task = Task.objects.create(
        title='Original Task Issue29',
        description='This is a test task for cloning functionality.',
        project=project,
        status=Task.STATUS_IN_PROGRESS,  # Will be reset to backlog in clone
        priority=Task.PRIORITY_HIGH,
        created_by=member_user,
        assigned_to_user=assignee_user,
        due_date=date.today() + timedelta(days=7),
        deadline=date.today() + timedelta(days=14),
        estimated_h=5.5,
        client=client
    )
    original_task.labels.set([label1, label2])
    original_task.watching_users.add(member_user)

    # Add comment (should NOT be cloned)
    Comment.objects.create(
        task=original_task,
        author=member_user,
        body='Test comment that should not be cloned'
    )

    # Add time entry (should NOT be cloned)
    TimeEntry.objects.create(
        task=original_task,
        user=member_user,
        started_at=timezone.now(),
        duration_m=60,
        note='Test time entry'
    )

    # Create subtasks
    subtask1 = Task.objects.create(
        title='Subtask 1 for Issue29',
        description='First subtask',
        project=project,
        status=Task.STATUS_TODO,
        priority=Task.PRIORITY_MEDIUM,
        created_by=member_user,
        assigned_to_user=assignee_user,
        parent_task=original_task
    )

    subtask2 = Task.objects.create(
        title='Subtask 2 for Issue29',
        description='Second subtask',
        project=project,
        status=Task.STATUS_DONE,
        priority=Task.PRIORITY_LOW,
        created_by=member_user,
        parent_task=original_task
    )

    # Create task assigned to team instead of user
    team_task = Task.objects.create(
        title='Team Task Issue29',
        description='Task assigned to team',
        project=project,
        status=Task.STATUS_REVIEW,
        priority=Task.PRIORITY_CRITICAL,
        created_by=member_user,
        assigned_to_team=team,
        due_date=date.today() + timedelta(days=3)
    )

    return {
        'member_user': member_user,
        'non_member_user': non_member_user,
        'assignee_user': assignee_user,
        'project': project,
        'original_task': original_task,
        'subtask1': subtask1,
        'subtask2': subtask2,
        'team_task': team_task,
        'label1': label1,
        'label2': label2,
        'client': client,
        'team': team,
    }


def test_clone_task_basic(data):
    """Test basic task cloning without subtasks."""
    print('\n=== Test: Basic Task Clone ===')
    client = Client()
    client.force_login(data['member_user'])

    original = data['original_task']
    original_id = original.pk

    # Perform clone
    url = reverse('tasks:task-clone', args=[original_id])
    response = client.post(url, {'include_subtasks': '0'})

    # Should redirect to new task detail page
    assert response.status_code == 302, f"Expected 302, got {response.status_code}"

    # Get the cloned task
    cloned_task = Task.objects.filter(title='[Kopie] Original Task Issue29').first()
    assert cloned_task is not None, "Cloned task not found"
    assert cloned_task.pk != original_id, "Clone has same ID as original"

    # Verify redirect URL
    expected_redirect = reverse('tasks:task-detail-full', args=[cloned_task.pk])
    assert response.url == expected_redirect, f"Expected redirect to {expected_redirect}, got {response.url}"

    # Verify cloned fields
    assert cloned_task.title == f'[Kopie] {original.title}', "Title not prefixed with [Kopie]"
    assert cloned_task.description == original.description, "Description not copied"
    assert cloned_task.project == original.project, "Project not copied"
    assert cloned_task.status == Task.STATUS_BACKLOG, f"Status not reset to backlog, got {cloned_task.status}"
    assert cloned_task.priority == original.priority, "Priority not copied"
    assert cloned_task.assigned_to_user == original.assigned_to_user, "Assigned user not copied"
    assert cloned_task.due_date == original.due_date, "Due date not copied"
    assert cloned_task.deadline == original.deadline, "Deadline not copied"
    assert cloned_task.estimated_h == original.estimated_h, "Estimated hours not copied"
    assert cloned_task.client == original.client, "Client not copied"
    assert cloned_task.created_by == data['member_user'], "Created by should be current user"

    # Verify labels were copied
    cloned_labels = set(cloned_task.labels.all())
    original_labels = set(original.labels.all())
    assert cloned_labels == original_labels, "Labels not copied correctly"

    # Verify things that should NOT be copied
    assert cloned_task.comments.count() == 0, "Comments should not be cloned"
    assert cloned_task.time_entries.count() == 0, "Time entries should not be cloned"
    assert cloned_task.watching_users.count() == 0, "Watchers should not be cloned"
    assert cloned_task.attachments.count() == 0, "Attachments should not be cloned"
    assert cloned_task.subtasks.count() == 0, "Subtasks should not be cloned when include_subtasks=0"

    print('✓ Basic task clone works correctly')
    print(f'✓ Clone has status: {cloned_task.status} (expected: backlog)')
    print(f'✓ Clone title: {cloned_task.title}')
    print(f'✓ Clone ID: {cloned_task.pk} (original: {original_id})')


def test_clone_task_with_subtasks(data):
    """Test task cloning with subtasks included."""
    print('\n=== Test: Clone Task with Subtasks ===')
    client = Client()
    client.force_login(data['member_user'])

    original = data['original_task']
    original_subtask_count = original.subtasks.count()

    # Perform clone with subtasks
    url = reverse('tasks:task-clone', args=[original.pk])
    response = client.post(url, {'include_subtasks': '1'})

    assert response.status_code == 302, f"Expected 302, got {response.status_code}"

    # Get the cloned task (find most recent one)
    cloned_task = Task.objects.filter(
        title='[Kopie] Original Task Issue29',
        parent_task__isnull=True
    ).order_by('-created_at').first()

    assert cloned_task is not None, "Cloned task not found"

    # Verify subtasks were cloned
    cloned_subtasks = cloned_task.subtasks.all()
    assert cloned_subtasks.count() == original_subtask_count, \
        f"Expected {original_subtask_count} subtasks, got {cloned_subtasks.count()}"

    # Verify subtask properties
    for subtask in cloned_subtasks:
        assert subtask.parent_task == cloned_task, "Subtask parent not set correctly"
        assert subtask.project == cloned_task.project, "Subtask project not inherited"
        assert subtask.status == Task.STATUS_BACKLOG, "Subtask status not reset to backlog"
        assert subtask.created_by == data['member_user'], "Subtask created_by not set"

    print('✓ Task cloned with subtasks successfully')
    print(f'✓ Cloned {cloned_subtasks.count()} subtasks')
    print(f'✓ All subtasks have status: backlog')


def test_clone_team_assigned_task(data):
    """Test cloning a task assigned to a team instead of a user."""
    print('\n=== Test: Clone Team-Assigned Task ===')
    client = Client()
    client.force_login(data['member_user'])

    team_task = data['team_task']

    # Perform clone
    url = reverse('tasks:task-clone', args=[team_task.pk])
    response = client.post(url)

    assert response.status_code == 302, f"Expected 302, got {response.status_code}"

    # Get the cloned task
    cloned_task = Task.objects.filter(title='[Kopie] Team Task Issue29').first()
    assert cloned_task is not None, "Cloned task not found"

    # Verify team assignment was copied
    assert cloned_task.assigned_to_team == data['team'], "Team assignment not copied"
    assert cloned_task.assigned_to_user is None, "User should be None when assigned to team"
    assert cloned_task.status == Task.STATUS_BACKLOG, "Status not reset to backlog"

    print('✓ Team-assigned task cloned correctly')
    print(f'✓ Clone assigned to team: {cloned_task.assigned_to_team.name}')


def test_clone_permission_denied(data):
    """Test that non-members cannot clone tasks."""
    print('\n=== Test: Clone Permission Denied for Non-Members ===')
    client = Client()
    client.force_login(data['non_member_user'])

    # Try to clone task as non-member
    url = reverse('tasks:task-clone', args=[data['original_task'].pk])
    response = client.post(url)

    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"

    print('✓ Non-members correctly denied permission to clone tasks')


def test_clone_url_pattern(data):
    """Test that the clone URL pattern is correctly configured."""
    print('\n=== Test: Clone URL Pattern ===')

    task_id = data['original_task'].pk
    url = reverse('tasks:task-clone', args=[task_id])

    expected_url = f'/tasks/{task_id}/clone/'
    assert url == expected_url, f"Expected URL {expected_url}, got {url}"

    print(f'✓ Clone URL pattern correct: {url}')


def test_clone_button_in_templates(data):
    """Test that clone button is present in templates."""
    print('\n=== Test: Clone Button in Templates ===')
    client = Client()
    client.force_login(data['member_user'])

    task_id = data['original_task'].pk

    # Test slide-over template
    url = reverse('tasks:task-detail', args=[task_id])
    response = client.get(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert f'/tasks/{task_id}/clone/' in content or 'clone' in content.lower(), "Clone URL not found in slide-over template"
    assert 'Task klonen' in content, "Clone button text not found in slide-over"
    assert 'include_subtasks' in content, "Subtasks checkbox not found in slide-over"

    # Test full detail template
    url = reverse('tasks:task-detail-full', args=[task_id])
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert f'/tasks/{task_id}/clone/' in content or 'clone' in content.lower(), "Clone URL not found in full detail template"
    assert 'Task klonen' in content, "Clone button text not found in full detail"
    assert 'include_subtasks' in content, "Subtasks checkbox not found in full detail"

    print('✓ Clone button present in slide-over template')
    print('✓ Clone button present in full detail template')


def test_htmx_clone_response(data):
    """Test that HTMX clone request returns card partial."""
    print('\n=== Test: HTMX Clone Response ===')
    client = Client()
    client.force_login(data['member_user'])

    # Perform clone with HTMX header
    url = reverse('tasks:task-clone', args=[data['original_task'].pk])
    response = client.post(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Should return card partial HTML
    content = response.content.decode('utf-8')
    assert 'task-card' in content or 'card' in content, "Response doesn't appear to be a card partial"

    print('✓ HTMX clone returns card partial correctly')


def run_all_tests():
    """Run all test cases."""
    print('=' * 60)
    print('ISSUE-29: Task Clone Feature - Acceptance Criteria Tests')
    print('=' * 60)

    data = setup_test_data()

    try:
        test_clone_url_pattern(data)
        test_clone_task_basic(data)
        test_clone_task_with_subtasks(data)
        test_clone_team_assigned_task(data)
        test_clone_permission_denied(data)
        test_clone_button_in_templates(data)
        test_htmx_clone_response(data)

        print('\n' + '=' * 60)
        print('✓ ALL TESTS PASSED')
        print('=' * 60)
        return True

    except AssertionError as e:
        print(f'\n✗ TEST FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
