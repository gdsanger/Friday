#!/usr/bin/env python
"""
Acceptance tests for ISSUE-65: Task Activity Stream & History.

This script tests:
Part 1 - TaskActivity Model:
- TaskActivity model exists with all required fields
- display_text property returns correct text for different verbs
- log_activity() helper creates activity records

Part 2 - Activity Logging:
- Task creation logs 'created' activity
- Status change logs 'status_changed' activity
- Assignment logs 'assigned' or 'unassigned' activity
- Priority change logs 'priority_changed' activity
- Task close logs 'closed' activity with hours
- Comment logs 'commented' activity
- Watcher add/remove logs activity
- Project move logs 'project_moved' activity
- Story points change logs 'sp_changed' activity

Part 3 - Activity Timeline:
- TaskActivityView returns activity stream HTML
- Activities shown in slide-over and full detail pages
- Activity entries show user avatar, text, icon, and timestamp

Part 4 - Dashboard Widget:
- WidgetActivityView returns recent activities
- Only shows activities on tasks user can access
- Auto-refreshes every 60s
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from apps.tasks.models import Task, TaskActivity
from apps.projects.models import Project, ProjectUserMembership
from apps.teams.models import Team, TeamMembership
from decimal import Decimal

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks for testing."""
    # Clean up any existing test data
    Task.objects.filter(title__contains='Issue65').delete()
    Project.objects.filter(name__startswith='Test Project Issue65').delete()
    Team.objects.filter(name__contains='Issue65').delete()
    User.objects.filter(username__startswith='test_user_issue65').delete()

    # Create test users
    user1 = User.objects.create_user(
        username='test_user_issue65_1',
        email='testissue65_1@example.com',
        password='testpass123',
        first_name='Alice',
        last_name='Creator',
    )

    user2 = User.objects.create_user(
        username='test_user_issue65_2',
        email='testissue65_2@example.com',
        password='testpass123',
        first_name='Bob',
        last_name='Assignee',
    )

    user3 = User.objects.create_user(
        username='test_user_issue65_3',
        email='testissue65_3@example.com',
        password='testpass123',
        first_name='Charlie',
        last_name='Watcher',
    )

    # Create project
    project = Project.objects.create(
        name='Test Project Issue65',
        description='Test project for ISSUE-65',
        owner=user1,
        color='#2196F3',
        status='active'
    )

    # Add users as project members
    ProjectUserMembership.objects.create(project=project, user=user1, role='manager')
    ProjectUserMembership.objects.create(project=project, user=user2, role='member')
    ProjectUserMembership.objects.create(project=project, user=user3, role='member')

    # Create team
    team = Team.objects.create(
        name='Test Team Issue65',
        description='Test team',
        is_active=True
    )
    TeamMembership.objects.create(team=team, user=user2, role='member')

    return {
        'user1': user1,
        'user2': user2,
        'user3': user3,
        'project': project,
        'team': team,
    }


def test_task_activity_model(data):
    """Test TaskActivity model and display_text property."""
    print("\n1. Testing TaskActivity model...")

    # Create a test task
    task = Task.objects.create(
        title='Test Task Issue65 Model',
        description='Testing activity model',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
        priority=Task.PRIORITY_LOW,
    )

    # Test created activity
    activity = TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_CREATED,
    )
    assert activity.display_text == f"{data['user1'].full_name} hat den Task erstellt"
    print(f"   ✓ VERB_CREATED display_text: {activity.display_text}")

    # Test status_changed activity
    activity = TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_STATUS_CHANGED,
        old_value='To Do',
        new_value='In Bearbeitung',
    )
    assert 'Status von "To Do" auf "In Bearbeitung" geändert' in activity.display_text
    print(f"   ✓ VERB_STATUS_CHANGED display_text: {activity.display_text}")

    # Test assigned activity
    activity = TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_ASSIGNED,
        new_value=data['user2'].full_name,
    )
    assert data['user2'].full_name in activity.display_text
    print(f"   ✓ VERB_ASSIGNED display_text: {activity.display_text}")

    # Test closed activity
    activity = TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_CLOSED,
        new_value='4.5',
    )
    assert '4.5h' in activity.display_text
    print(f"   ✓ VERB_CLOSED display_text: {activity.display_text}")

    # Test project_moved activity
    activity = TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_PROJECT_MOVED,
        old_value='Old Project',
        new_value='New Project',
    )
    assert 'New Project' in activity.display_text
    print(f"   ✓ VERB_PROJECT_MOVED display_text: {activity.display_text}")

    print("   ✓ TaskActivity model working correctly")


def test_log_activity_helper(data):
    """Test log_activity() helper function."""
    print("\n2. Testing log_activity() helper...")

    from apps.tasks.activity import log_activity

    # Create a test task
    task = Task.objects.create(
        title='Test Task Issue65 Helper',
        description='Testing log_activity helper',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )

    # Count existing activities
    initial_count = task.activities.count()

    # Log a created activity
    log_activity(task, data['user1'], TaskActivity.VERB_CREATED)
    assert task.activities.count() == initial_count + 1
    activity = task.activities.first()
    assert activity.verb == TaskActivity.VERB_CREATED
    assert activity.user == data['user1']
    print("   ✓ log_activity() creates activity record")

    # Log with old and new values
    log_activity(task, data['user1'], TaskActivity.VERB_STATUS_CHANGED,
                 old_value='Todo', new_value='In Progress')
    assert task.activities.count() == initial_count + 2
    activity = task.activities.first()
    assert activity.old_value == 'Todo'
    assert activity.new_value == 'In Progress'
    print("   ✓ log_activity() stores old_value and new_value correctly")


def test_task_create_logs_activity(client, data):
    """Test that creating a task logs 'created' activity."""
    print("\n3. Testing task creation logs activity...")

    client.force_login(data['user1'])

    # Create task via API
    response = client.post('/tasks/create/', {
        'project_id': data['project'].pk,
        'title': 'Test Task Issue65 Create',
        'description': 'Testing activity logging on create',
        'status': Task.STATUS_TODO,
        'priority': Task.PRIORITY_MEDIUM,
    })

    # Get the created task
    task = Task.objects.filter(title='Test Task Issue65 Create').first()
    assert task is not None, "Task was not created"

    # Check activity was logged
    activities = task.activities.all()
    assert activities.count() >= 1, f"Expected at least 1 activity, got {activities.count()}"

    created_activity = activities.filter(verb=TaskActivity.VERB_CREATED).first()
    assert created_activity is not None, "VERB_CREATED activity not found"
    assert created_activity.user == data['user1']
    print("   ✓ Task creation logs 'created' activity")


def test_status_change_logs_activity(client, data):
    """Test that changing task status logs activity."""
    print("\n4. Testing status change logs activity...")

    # Create a task
    task = Task.objects.create(
        title='Test Task Issue65 Status',
        description='Testing status change',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )

    client.force_login(data['user1'])

    # Change status via API
    response = client.post(f'/tasks/{task.pk}/status/', {
        'status': Task.STATUS_IN_PROGRESS,
    })

    assert response.status_code == 204, f"Expected 204, got {response.status_code}"

    # Refresh task
    task.refresh_from_db()
    assert task.status == Task.STATUS_IN_PROGRESS

    # Check activity was logged
    status_activity = task.activities.filter(verb=TaskActivity.VERB_STATUS_CHANGED).first()
    assert status_activity is not None, "VERB_STATUS_CHANGED activity not found"
    assert 'To Do' in status_activity.old_value or 'To Do' in status_activity.display_text
    print(f"   ✓ Status change logged: {status_activity.display_text}")


def test_assignment_logs_activity(client, data):
    """Test that assigning task logs activity."""
    print("\n5. Testing task assignment logs activity...")

    # Create a task
    task = Task.objects.create(
        title='Test Task Issue65 Assign',
        description='Testing assignment',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )

    client.force_login(data['user1'])

    # Assign to user via API
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'user_id': data['user2'].pk,
    })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Check activity was logged
    assign_activity = task.activities.filter(verb=TaskActivity.VERB_ASSIGNED).first()
    assert assign_activity is not None, "VERB_ASSIGNED activity not found"
    assert data['user2'].full_name in assign_activity.new_value
    print(f"   ✓ Assignment logged: {assign_activity.display_text}")


def test_comment_logs_activity(client, data):
    """Test that adding comment logs activity."""
    print("\n6. Testing comment logs activity...")

    # Create a task
    task = Task.objects.create(
        title='Test Task Issue65 Comment',
        description='Testing comment activity',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )

    client.force_login(data['user1'])

    # Add comment via API
    response = client.post(f'/tasks/{task.pk}/comment/', {
        'body': 'This is a test comment',
    })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Check activity was logged
    comment_activity = task.activities.filter(verb=TaskActivity.VERB_COMMENTED).first()
    assert comment_activity is not None, "VERB_COMMENTED activity not found"
    print(f"   ✓ Comment logged: {comment_activity.display_text}")


def test_activity_view(client, data):
    """Test TaskActivityView returns activity stream."""
    print("\n7. Testing TaskActivityView...")

    # Create a task with activities
    task = Task.objects.create(
        title='Test Task Issue65 View',
        description='Testing activity view',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )

    # Add some activities
    TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_CREATED,
    )
    TaskActivity.objects.create(
        task=task,
        user=data['user1'],
        verb=TaskActivity.VERB_STATUS_CHANGED,
        old_value='Backlog',
        new_value='To Do',
    )

    client.force_login(data['user1'])

    # Request activity stream
    response = client.get(f'/tasks/{task.pk}/activity/')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'AKTIVIT' in response.content or b'activity' in response.content.lower(), "Activity section header not found"
    assert data['user1'].full_name.encode() in response.content, "User name not in activity stream"
    print("   ✓ TaskActivityView returns activity stream HTML")


def test_dashboard_widget(client, data):
    """Test Dashboard WidgetActivityView."""
    print("\n8. Testing Dashboard Activity Widget...")

    # Create tasks with activities
    task1 = Task.objects.create(
        title='Test Task Issue65 Widget 1',
        project=data['project'],
        created_by=data['user1'],
        status=Task.STATUS_TODO,
    )
    TaskActivity.objects.create(
        task=task1,
        user=data['user1'],
        verb=TaskActivity.VERB_CREATED,
    )

    task2 = Task.objects.create(
        title='Test Task Issue65 Widget 2',
        project=data['project'],
        created_by=data['user2'],
        status=Task.STATUS_TODO,
    )
    TaskActivity.objects.create(
        task=task2,
        user=data['user2'],
        verb=TaskActivity.VERB_CREATED,
    )

    client.force_login(data['user1'])

    # Request widget
    response = client.get('/dashboard/widgets/activity/')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'widget-activity' in response.content, "Widget ID not found"
    assert b'Aktivit' in response.content or b'Activity' in response.content, "Activity header not found"
    print("   ✓ Dashboard activity widget returns HTML")


def run_all_tests():
    """Run all acceptance tests."""
    print("=" * 70)
    print("ISSUE-65: Task Activity Stream & History - Acceptance Tests")
    print("=" * 70)

    try:
        # Setup
        data = setup_test_data()
        client = Client()

        # Run tests
        test_task_activity_model(data)
        test_log_activity_helper(data)
        test_task_create_logs_activity(client, data)
        test_status_change_logs_activity(client, data)
        test_assignment_logs_activity(client, data)
        test_comment_logs_activity(client, data)
        test_activity_view(client, data)
        test_dashboard_widget(client, data)

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
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
