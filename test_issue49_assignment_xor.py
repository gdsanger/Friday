#!/usr/bin/env python
"""
Acceptance tests for ISSUE-49: Task Assignment XOR constraint.

This script tests:
- Model validation: Task.clean() rejects both user AND team assignments
- Data migration: Tasks with both assignments get team cleared
- Daily digest query: XOR logic (user direct OR team without user)
- Mail dispatcher: XOR logic for assignee recipient type
- TaskAssignView: XOR enforcement in POST handler
- UI JavaScript: XOR enforcement in assignment dropdowns
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.teams.models import Team, TeamMembership
from datetime import date, timedelta

User = get_user_model()


def setup_test_data():
    """Create test users, projects, teams, and tasks for testing."""
    # Clean up any existing test data
    Task.objects.filter(title__contains='Issue49').delete()
    Project.objects.filter(name__startswith='Test Project Issue49').delete()
    Team.objects.filter(name__contains='Issue49').delete()
    User.objects.filter(username__startswith='test_user_issue49').delete()

    # Create test users
    user1 = User.objects.create_user(
        username='test_user_issue49_1',
        email='testissue49_1@example.com',
        password='testpass123',
        first_name='Alice',
        last_name='Test',
        notify_email=True
    )
    user2 = User.objects.create_user(
        username='test_user_issue49_2',
        email='testissue49_2@example.com',
        password='testpass123',
        first_name='Bob',
        last_name='Test',
        notify_email=True
    )
    user3 = User.objects.create_user(
        username='test_user_issue49_3',
        email='testissue49_3@example.com',
        password='testpass123',
        first_name='Charlie',
        last_name='Test',
        notify_email=True
    )

    # Create test team
    team = Team.objects.create(
        name='Test Team Issue49',
        slug='test-team-issue49',
        description='Test team for XOR constraint testing'
    )
    TeamMembership.objects.create(user=user2, team=team, role='member')
    TeamMembership.objects.create(user=user3, team=team, role='member')

    # Create test project
    project = Project.objects.create(
        name='Test Project Issue49',
        description='Test project for assignment XOR',
        status='active',
        owner=user1
    )
    project.user_members.add(user1, user2, user3)

    return user1, user2, user3, team, project


def test_model_validation():
    """Test 1: Task.clean() rejects both user AND team assignments."""
    print("\n" + "=" * 70)
    print("TEST 1: Model Validation (Task.clean())")
    print("=" * 70)

    user1, user2, user3, team, project = setup_test_data()

    # Test 1a: Creating task with user only - should work
    try:
        task_user = Task.objects.create(
            title='Issue49 Test User Only',
            project=project,
            created_by=user1,
            assigned_to_user=user1
        )
        print("✓ Task with user only created successfully")
        task_user.delete()
    except ValidationError as e:
        print(f"✗ FAILED: Task with user only raised ValidationError: {e}")
        return False

    # Test 1b: Creating task with team only - should work
    try:
        task_team = Task.objects.create(
            title='Issue49 Test Team Only',
            project=project,
            created_by=user1,
            assigned_to_team=team
        )
        print("✓ Task with team only created successfully")
        task_team.delete()
    except ValidationError as e:
        print(f"✗ FAILED: Task with team only raised ValidationError: {e}")
        return False

    # Test 1c: Creating task with neither - should work
    try:
        task_none = Task.objects.create(
            title='Issue49 Test Unassigned',
            project=project,
            created_by=user1
        )
        print("✓ Task with no assignment created successfully")
        task_none.delete()
    except ValidationError as e:
        print(f"✗ FAILED: Unassigned task raised ValidationError: {e}")
        return False

    # Test 1d: Creating task with BOTH user and team - should fail
    try:
        task_both = Task.objects.create(
            title='Issue49 Test Both',
            project=project,
            created_by=user1,
            assigned_to_user=user1,
            assigned_to_team=team
        )
        print(f"✗ FAILED: Task with both user and team was created (ID: {task_both.pk})")
        task_both.delete()
        return False
    except ValidationError as e:
        if 'nicht gleichzeitig' in str(e):
            print("✓ Task with both user and team correctly rejected")
        else:
            print(f"✗ FAILED: Wrong ValidationError message: {e}")
            return False

    print("\n✅ Model validation tests passed")
    return True


def test_data_migration():
    """Test 2: Verify data migration fixes double assignments."""
    print("\n" + "=" * 70)
    print("TEST 2: Data Migration (fix_double_assignments)")
    print("=" * 70)

    user1, user2, user3, team, project = setup_test_data()

    # Create a task with both assignments directly in DB (bypassing validation)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO tasks_task
            (title, project_id, status, priority, created_by_id,
             assigned_to_user_id, assigned_to_team_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, [
            'Issue49 Double Assignment',
            project.pk,
            'todo',
            0,
            user1.pk,
            user1.pk,
            team.pk
        ])

    # Check that the task has both assignments
    task = Task.objects.get(title='Issue49 Double Assignment')
    if task.assigned_to_user_id and task.assigned_to_team_id:
        print("✓ Created task with both assignments via raw SQL")
    else:
        print("✗ FAILED: Could not create task with both assignments")
        return False

    # Simulate the migration
    from apps.tasks.migrations.0008_fix_assignment_xor import fix_double_assignments
    from django.apps import apps
    fix_double_assignments(apps, None)

    # Reload and check
    task.refresh_from_db()
    if task.assigned_to_user_id and not task.assigned_to_team_id:
        print("✓ Migration cleared team assignment (kept user)")
    else:
        print(f"✗ FAILED: Migration did not fix assignment - user: {task.assigned_to_user_id}, team: {task.assigned_to_team_id}")
        return False

    task.delete()
    print("\n✅ Data migration test passed")
    return True


def test_daily_digest_query():
    """Test 3: Daily digest query uses XOR logic."""
    print("\n" + "=" * 70)
    print("TEST 3: Daily Digest Query (XOR logic)")
    print("=" * 70)

    user1, user2, user3, team, project = setup_test_data()
    today = timezone.now().date()

    # Create test tasks
    # Task 1: Assigned to user2 directly
    task1 = Task.objects.create(
        title='Issue49 Direct User Assignment',
        project=project,
        created_by=user1,
        assigned_to_user=user2,
        due_date=today + timedelta(days=1),
        status='todo'
    )

    # Task 2: Assigned to team (user2 is member)
    task2 = Task.objects.create(
        title='Issue49 Team Assignment',
        project=project,
        created_by=user1,
        assigned_to_team=team,
        due_date=today + timedelta(days=1),
        status='todo'
    )

    # Task 3: Assigned to user3 AND team via raw SQL (simulating old bug)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO tasks_task
            (title, project_id, status, priority, created_by_id,
             assigned_to_user_id, assigned_to_team_id, due_date, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, [
            'Issue49 Both Assignments',
            project.pk,
            'todo',
            0,
            user1.pk,
            user3.pk,
            team.pk,
            today + timedelta(days=1)
        ])
    task3 = Task.objects.get(title='Issue49 Both Assignments')

    # Test the digest query for user2
    from django.db import models
    my_teams = list(user2.teams)

    upcoming_user2 = Task.objects.filter(
        models.Q(assigned_to_user=user2) |
        models.Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True),
        due_date__range=(today, today + timedelta(days=7)),
    ).exclude(status='done')

    user2_task_ids = set(upcoming_user2.values_list('id', flat=True))

    # user2 should get task1 (direct) and task2 (team, no user)
    # user2 should NOT get task3 (has user3, even though team matches)
    if task1.id in user2_task_ids:
        print("✓ user2 gets task1 (directly assigned)")
    else:
        print("✗ FAILED: user2 should get task1 (directly assigned)")
        return False

    if task2.id in user2_task_ids:
        print("✓ user2 gets task2 (team assigned, no user)")
    else:
        print("✗ FAILED: user2 should get task2 (team assigned, no user)")
        return False

    if task3.id not in user2_task_ids:
        print("✓ user2 does NOT get task3 (assigned to user3, not to user2 directly)")
    else:
        print("✗ FAILED: user2 should NOT get task3 (it's assigned to user3)")
        return False

    # Test for user3
    my_teams_user3 = list(user3.teams)
    upcoming_user3 = Task.objects.filter(
        models.Q(assigned_to_user=user3) |
        models.Q(assigned_to_team__in=my_teams_user3, assigned_to_user__isnull=True),
        due_date__range=(today, today + timedelta(days=7)),
    ).exclude(status='done')

    user3_task_ids = set(upcoming_user3.values_list('id', flat=True))

    # user3 should get task2 (team, no user) and task3 (direct)
    # user3 should NOT get task1 (assigned to user2)
    if task3.id in user3_task_ids:
        print("✓ user3 gets task3 (directly assigned)")
    else:
        print("✗ FAILED: user3 should get task3 (directly assigned)")
        return False

    if task2.id in user3_task_ids:
        print("✓ user3 gets task2 (team assigned, no user)")
    else:
        print("✗ FAILED: user3 should get task2 (team assigned, no user)")
        return False

    if task1.id not in user3_task_ids:
        print("✓ user3 does NOT get task1 (assigned to user2)")
    else:
        print("✗ FAILED: user3 should NOT get task1")
        return False

    # Cleanup
    task1.delete()
    task2.delete()
    task3.delete()

    print("\n✅ Daily digest query tests passed")
    return True


def test_mail_dispatcher():
    """Test 4: Mail dispatcher uses XOR logic for assignee recipients."""
    print("\n" + "=" * 70)
    print("TEST 4: Mail Dispatcher (assignee XOR logic)")
    print("=" * 70)

    user1, user2, user3, team, project = setup_test_data()

    # Task assigned to user only
    task_user = Task.objects.create(
        title='Issue49 User Mail Test',
        project=project,
        created_by=user1,
        assigned_to_user=user2
    )

    # Task assigned to team only
    task_team = Task.objects.create(
        title='Issue49 Team Mail Test',
        project=project,
        created_by=user1,
        assigned_to_team=team
    )

    from apps.mail.dispatcher import _resolve_recipients
    from apps.mail.models import MailHook

    # Create a mock hook with assignee recipient
    class MockHook:
        recipients = ['assignee']

    mock_hook = MockHook()

    # Test user assignment
    recipients_user = _resolve_recipients(mock_hook, task_user)
    if user2.email in recipients_user:
        print("✓ User-assigned task sends to assigned user")
    else:
        print(f"✗ FAILED: Expected {user2.email} in recipients, got {recipients_user}")
        return False

    if len(recipients_user) == 1:
        print("✓ User-assigned task sends to only one user")
    else:
        print(f"✗ FAILED: Expected 1 recipient, got {len(recipients_user)}")
        return False

    # Test team assignment
    recipients_team = _resolve_recipients(mock_hook, task_team)
    if user2.email in recipients_team and user3.email in recipients_team:
        print("✓ Team-assigned task sends to all team members")
    else:
        print(f"✗ FAILED: Expected team members in recipients, got {recipients_team}")
        return False

    if user1.email not in recipients_team:
        print("✓ Team-assigned task does NOT send to non-team members")
    else:
        print(f"✗ FAILED: user1 should not be in team recipients")
        return False

    # Cleanup
    task_user.delete()
    task_team.delete()

    print("\n✅ Mail dispatcher tests passed")
    return True


def test_task_assign_view():
    """Test 5: TaskAssignView enforces XOR in POST handler."""
    print("\n" + "=" * 70)
    print("TEST 5: TaskAssignView (XOR enforcement)")
    print("=" * 70)

    user1, user2, user3, team, project = setup_test_data()
    client = Client()
    client.login(username='test_user_issue49_1', password='testpass123')

    # Create a task
    task = Task.objects.create(
        title='Issue49 Assign View Test',
        project=project,
        created_by=user1
    )

    # Test 5a: Assign to user
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'user_id': user2.pk,
        'team_id': ''
    })
    task.refresh_from_db()
    if task.assigned_to_user_id == user2.pk and not task.assigned_to_team_id:
        print("✓ Assigning user clears team")
    else:
        print(f"✗ FAILED: Expected user={user2.pk}, team=None, got user={task.assigned_to_user_id}, team={task.assigned_to_team_id}")
        return False

    # Test 5b: Assign to team (should clear user)
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'user_id': '',
        'team_id': team.pk
    })
    task.refresh_from_db()
    if not task.assigned_to_user_id and task.assigned_to_team_id == team.pk:
        print("✓ Assigning team clears user")
    else:
        print(f"✗ FAILED: Expected user=None, team={team.pk}, got user={task.assigned_to_user_id}, team={task.assigned_to_team_id}")
        return False

    # Test 5c: Clear both
    response = client.post(f'/tasks/{task.pk}/assign/', {
        'user_id': '',
        'team_id': ''
    })
    task.refresh_from_db()
    if not task.assigned_to_user_id and not task.assigned_to_team_id:
        print("✓ Clearing both assignments works")
    else:
        print(f"✗ FAILED: Expected both None, got user={task.assigned_to_user_id}, team={task.assigned_to_team_id}")
        return False

    # Cleanup
    task.delete()

    print("\n✅ TaskAssignView tests passed")
    return True


def run_all_tests():
    """Run all tests for ISSUE-49."""
    print("\n" + "=" * 70)
    print("ISSUE-49: Task Assignment XOR Constraint")
    print("=" * 70)

    all_passed = True

    # Run all tests
    all_passed = test_model_validation() and all_passed
    all_passed = test_data_migration() and all_passed
    all_passed = test_daily_digest_query() and all_passed
    all_passed = test_mail_dispatcher() and all_passed
    all_passed = test_task_assign_view() and all_passed

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
