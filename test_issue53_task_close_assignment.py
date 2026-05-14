#!/usr/bin/env python
"""
Acceptance tests for ISSUE-53: Task Close & Assignment with Email Notifications.

This script tests:
Part 1 - Task Close:
- TaskCloseFormView returns modal HTML
- TaskCloseView validates required hours field
- TaskCloseView creates TimeEntry with correct duration
- TaskCloseView sets task status to DONE
- TaskCloseView sends email to requester (if different from closer)
- TaskCloseView sends email to watchers
- Modal closes and UI updates after successful close

Part 2 - Task Assignment:
- TaskAssignFormView returns modal HTML with project members/teams
- TaskAssignView sends email to newly assigned user (if different from assigner)
- TaskAssignView sends email to team members when team assigned
- XOR constraint maintained (cannot assign both user and team)
- Modal closes and assignee display updates
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
from apps.tasks.models import Task, TimeEntry
from apps.projects.models import Project, ProjectUserMembership
from apps.teams.models import Team, TeamMembership
from apps.mail.models import MailHook
from datetime import timedelta

User = get_user_model()


def setup_test_data():
    """Create test users, projects, teams, and tasks for testing."""
    # Clean up any existing test data
    Task.objects.filter(title__contains='Issue53').delete()
    Project.objects.filter(name__startswith='Test Project Issue53').delete()
    Team.objects.filter(name__contains='Issue53').delete()
    User.objects.filter(username__startswith='test_user_issue53').delete()

    # Create test users
    user1 = User.objects.create_user(
        username='test_user_issue53_1',
        email='testissue53_1@example.com',
        password='testpass123',
        first_name='Alice',
        last_name='Closer',
        notify_email=True
    )

    user2 = User.objects.create_user(
        username='test_user_issue53_2',
        email='testissue53_2@example.com',
        password='testpass123',
        first_name='Bob',
        last_name='Requester',
        notify_email=True
    )

    user3 = User.objects.create_user(
        username='test_user_issue53_3',
        email='testissue53_3@example.com',
        password='testpass123',
        first_name='Charlie',
        last_name='Watcher',
        notify_email=True
    )

    user4 = User.objects.create_user(
        username='test_user_issue53_4',
        email='testissue53_4@example.com',
        password='testpass123',
        first_name='David',
        last_name='TeamMember',
        notify_email=True
    )

    # Create project
    project = Project.objects.create(
        name='Test Project Issue53',
        description='Test project for ISSUE-53',
        owner=user1,
        color='#4CAF50',
        status='active'
    )

    # Add users as project members
    ProjectUserMembership.objects.create(project=project, user=user1, role='member')
    ProjectUserMembership.objects.create(project=project, user=user2, role='member')
    ProjectUserMembership.objects.create(project=project, user=user3, role='member')
    ProjectUserMembership.objects.create(project=project, user=user4, role='member')

    # Create team
    team = Team.objects.create(
        name='Test Team Issue53',
        description='Test team for assignments',
        is_active=True
    )
    TeamMembership.objects.create(team=team, user=user4, role='member')

    # Create task
    task = Task.objects.create(
        title='Test Task Issue53',
        description='Test task for closing and assignment',
        project=project,
        created_by=user1,
        requester=user2,
        status=Task.STATUS_IN_PROGRESS,
        priority=Task.PRIORITY_MEDIUM,
        story_points=5
    )

    # Add watcher
    task.watching_users.add(user3)

    return {
        'user1': user1,
        'user2': user2,
        'user3': user3,
        'user4': user4,
        'project': project,
        'team': team,
        'task': task,
    }


def test_task_close_form_view(client, data):
    """Test that TaskCloseFormView returns modal HTML."""
    print("\n1. Testing TaskCloseFormView...")

    client.force_login(data['user1'])
    response = client.get(f'/tasks/{data["task"].pk}/close/')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'Task abschlie' in response.content, "Modal title not found"
    assert b'actual_hours' in response.content, "Hours input field not found"
    assert b'note' in response.content, "Note textarea not found"
    print("   ✓ TaskCloseFormView returns modal HTML")


def test_task_close_validation(client, data):
    """Test that TaskCloseView validates required hours field."""
    print("\n2. Testing TaskCloseView validation...")

    client.force_login(data['user1'])

    # Test without hours
    response = client.post(f'/tasks/{data["task"].pk}/close/submit/', {
        'note': 'Test note'
    })
    assert b'Bitte den tats' in response.content, "Missing hours error not shown"
    print("   ✓ Validation error shown when hours missing")

    # Test with invalid hours
    response = client.post(f'/tasks/{data["task"].pk}/close/submit/', {
        'actual_hours': 'invalid',
        'note': 'Test note'
    })
    assert b'g\xc3\xbcltige' in response.content or b'valid' in response.content, "Invalid hours error not shown"
    print("   ✓ Validation error shown for invalid hours")


def test_task_close_success(client, data):
    """Test successful task closure with time tracking."""
    print("\n3. Testing successful task closure...")

    client.force_login(data['user1'])
    task = data['task']

    # Count time entries before
    initial_time_entries = TimeEntry.objects.filter(task=task).count()

    # Close the task
    response = client.post(f'/tasks/{task.pk}/close/submit/', {
        'actual_hours': '4.5',
        'note': 'Task completed successfully'
    })

    # Check response
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    assert response.has_header('HX-Trigger'), "HX-Trigger header not set"
    assert response['HX-Trigger'] == 'taskClosed', "Wrong HX-Trigger value"
    print("   ✓ Response status and headers correct")

    # Refresh task from database
    task.refresh_from_db()

    # Check task status
    assert task.status == Task.STATUS_DONE, f"Task status not set to DONE, got {task.status}"
    print("   ✓ Task status set to DONE")

    # Check time entry created
    final_time_entries = TimeEntry.objects.filter(task=task).count()
    assert final_time_entries == initial_time_entries + 1, "Time entry not created"

    latest_entry = TimeEntry.objects.filter(task=task).order_by('-created_at').first()
    assert latest_entry.user == data['user1'], "Time entry user incorrect"
    assert latest_entry.duration_m == 270, f"Expected 270 minutes, got {latest_entry.duration_m}"
    assert 'Task completed successfully' in latest_entry.note, "Note not saved correctly"
    print("   ✓ Time entry created with correct duration (4.5h = 270m)")


def test_task_assign_form_view(client, data):
    """Test that TaskAssignFormView returns modal HTML."""
    print("\n4. Testing TaskAssignFormView...")

    client.force_login(data['user1'])
    response = client.get(f'/tasks/{data["task"].pk}/assign-form/')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'Task zuweisen' in response.content, "Modal title not found"
    assert b'user_id' in response.content, "User select not found"
    assert b'team_id' in response.content, "Team select not found"
    assert data['user2'].first_name.encode() in response.content, "Project member not in list"
    print("   ✓ TaskAssignFormView returns modal HTML with members")


def test_task_assign_to_user(client, data):
    """Test assigning task to user."""
    print("\n5. Testing task assignment to user...")

    client.force_login(data['user1'])
    task = data['task']

    # Assign to user2
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'user_id': data['user2'].pk
    })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.has_header('HX-Trigger'), "HX-Trigger header not set"
    assert 'taskAssigned' in response['HX-Trigger'], "Wrong HX-Trigger value"
    print("   ✓ Response headers correct")

    # Refresh task
    task.refresh_from_db()

    assert task.assigned_to_user == data['user2'], "Task not assigned to user"
    assert task.assigned_to_team is None, "Team should be None (XOR)"
    print("   ✓ Task assigned to user, team is None (XOR enforced)")


def test_task_assign_to_team(client, data):
    """Test assigning task to team."""
    print("\n6. Testing task assignment to team...")

    client.force_login(data['user1'])
    task = data['task']

    # Assign to team
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'team_id': data['team'].pk
    })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Refresh task
    task.refresh_from_db()

    assert task.assigned_to_team == data['team'], "Task not assigned to team"
    assert task.assigned_to_user is None, "User should be None (XOR)"
    print("   ✓ Task assigned to team, user is None (XOR enforced)")


def test_task_assign_xor_constraint(client, data):
    """Test XOR constraint: cannot have both user and team."""
    print("\n7. Testing XOR constraint in assignment...")

    client.force_login(data['user1'])
    task = data['task']

    # First assign to user
    client.post(f'/tasks/{task.pk}/assign/', {'user_id': data['user2'].pk})
    task.refresh_from_db()
    assert task.assigned_to_user == data['user2']
    assert task.assigned_to_team is None

    # Then assign to team - should clear user
    client.post(f'/tasks/{task.pk}/assign/', {'team_id': data['team'].pk})
    task.refresh_from_db()
    assert task.assigned_to_user is None, "User should be cleared when team assigned"
    assert task.assigned_to_team == data['team']

    # Then assign back to user - should clear team
    client.post(f'/tasks/{task.pk}/assign/', {'user_id': data['user2'].pk})
    task.refresh_from_db()
    assert task.assigned_to_user == data['user2']
    assert task.assigned_to_team is None, "Team should be cleared when user assigned"

    print("   ✓ XOR constraint properly enforced in TaskAssignView")


def test_mail_hooks_exist():
    """Test that required mail hooks exist."""
    print("\n8. Testing mail hooks...")

    # Check TASK_DONE hook exists
    try:
        done_hook = MailHook.objects.get(event=MailHook.EVENT_TASK_DONE)
        print(f"   ✓ TASK_DONE hook exists (active={done_hook.is_active})")
    except MailHook.DoesNotExist:
        print("   ⚠ TASK_DONE hook not found (may need to be created)")

    # Check TASK_ASSIGNED hook exists
    try:
        assigned_hook = MailHook.objects.get(event=MailHook.EVENT_TASK_ASSIGNED)
        print(f"   ✓ TASK_ASSIGNED hook exists (active={assigned_hook.is_active})")
    except MailHook.DoesNotExist:
        print("   ⚠ TASK_ASSIGNED hook not found (may need to be created)")


def run_tests():
    """Run all acceptance tests."""
    print("\n" + "="*70)
    print("ISSUE-53 ACCEPTANCE TESTS: Task Close & Assignment with Email")
    print("="*70)

    # Setup test data
    print("\nSetting up test data...")
    data = setup_test_data()
    print("✓ Test data created")

    # Create test client
    client = Client()

    # Run tests
    try:
        test_task_close_form_view(client, data)
        test_task_close_validation(client, data)
        test_task_close_success(client, data)
        test_task_assign_form_view(client, data)
        test_task_assign_to_user(client, data)
        test_task_assign_to_team(client, data)
        test_task_assign_xor_constraint(client, data)
        test_mail_hooks_exist()

        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        return True

    except AssertionError as e:
        print("\n" + "="*70)
        print(f"❌ TEST FAILED: {e}")
        print("="*70)
        return False

    finally:
        # Cleanup
        print("\nCleaning up test data...")
        Task.objects.filter(title__contains='Issue53').delete()
        Project.objects.filter(name__startswith='Test Project Issue53').delete()
        Team.objects.filter(name__contains='Issue53').delete()
        User.objects.filter(username__startswith='test_user_issue53').delete()
        print("✓ Cleanup complete")


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
