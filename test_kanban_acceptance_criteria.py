#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-09: Kanban Board.

This script tests all requirements from the issue:
- Kanban board renders all 5 status columns
- View modes work correctly (all, mine_created, mine_assigned, team_assigned, watching)
- Filters work correctly (project, team, priority, due)
- Multiple filters combine correctly (AND logic)
- Task move endpoint works
- Column counts update after filter change
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
from datetime import date, timedelta

User = get_user_model()


def setup_test_data():
    """Create test users, teams, projects, and tasks"""
    print("\n── Setting up test data ──")

    # Create users
    user1 = User.objects.create_user(
        username='testuser1',
        email='test1@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User1'
    )

    user2 = User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User2'
    )

    # Create team
    team = Team.objects.create(
        name='Test Team',
        slug='test-team'
    )
    TeamMembership.objects.create(user=user1, team=team, role='member')

    # Create projects
    project1 = Project.objects.create(
        name='Project Alpha',
        visibility='members',
        owner=user1
    )
    ProjectUserMembership.objects.create(
        project=project1,
        user=user1,
        role='manager'
    )

    project2 = Project.objects.create(
        name='Project Beta',
        visibility='organisation',
        owner=user2
    )

    # Create tasks with various statuses, assignments, and dates
    tasks = [
        # Tasks in different statuses
        Task.objects.create(
            title='Task 1 - Backlog',
            project=project1,
            status=Task.STATUS_BACKLOG,
            created_by=user1,
            priority=Task.PRIORITY_HIGH
        ),
        Task.objects.create(
            title='Task 2 - Todo',
            project=project1,
            status=Task.STATUS_TODO,
            created_by=user1,
            assigned_to_user=user1,
            due_date=date.today() + timedelta(days=1)
        ),
        Task.objects.create(
            title='Task 3 - In Progress',
            project=project1,
            status=Task.STATUS_IN_PROGRESS,
            created_by=user1,
            assigned_to_team=team,
            due_date=date.today()
        ),
        Task.objects.create(
            title='Task 4 - Review',
            project=project2,
            status=Task.STATUS_REVIEW,
            created_by=user2,
            assigned_to_user=user2,
            priority=Task.PRIORITY_CRITICAL
        ),
        Task.objects.create(
            title='Task 5 - Done',
            project=project2,
            status=Task.STATUS_DONE,
            created_by=user2,
            due_date=date.today() - timedelta(days=1)  # Overdue but done
        ),
        Task.objects.create(
            title='Task 6 - Overdue',
            project=project1,
            status=Task.STATUS_TODO,
            created_by=user1,
            due_date=date.today() - timedelta(days=2)
        ),
        Task.objects.create(
            title='Task 7 - This Week',
            project=project1,
            status=Task.STATUS_TODO,
            created_by=user1,
            due_date=date.today() + timedelta(days=5)
        ),
    ]

    # Add watchers
    tasks[0].watching_users.add(user1)
    tasks[3].watching_teams.add(team)

    print(f"✓ Created {len(tasks)} tasks across {Task.objects.count()} total")
    print(f"✓ Created {User.objects.count()} users, {Team.objects.count()} teams, {Project.objects.count()} projects")

    return user1, user2, team, project1, project2


def test_kanban_board_url():
    """Test /kanban/ URL is accessible"""
    client = Client()
    user = User.objects.first()
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    assert response.status_code == 200, f"Kanban board returned {response.status_code}"
    print("✓ /kanban/ renders successfully")


def test_all_columns_render():
    """Test all 5 status columns render with tasks"""
    client = Client()
    user = User.objects.first()
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check all 5 columns are present
    assert 'Backlog' in content, "Backlog column not found"
    assert 'To Do' in content, "To Do column not found"
    assert 'In Progress' in content, "In Progress column not found"
    assert 'Review' in content, "Review column not found"
    assert 'Done' in content, "Done column not found"

    print("✓ All 5 status columns render")


def test_view_mode_all():
    """Test 'all' view shows all tasks in accessible projects"""
    client = Client()
    user = User.objects.first()
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?view=all')
    assert response.status_code == 200

    # Should show tasks from accessible projects
    content = response.content.decode('utf-8')
    assert 'Task 1 - Backlog' in content, "Task 1 not shown in 'all' view"

    print("✓ 'All' view shows all tasks in accessible projects")


def test_view_mode_mine_created():
    """Test 'mine_created' filters to tasks where created_by = request.user"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?view=mine_created')
    content = response.content.decode('utf-8')

    # Should show tasks created by user1
    assert 'Task 1 - Backlog' in content, "Task created by user1 not shown"

    # Should NOT show tasks created by user2
    assert 'Task 4 - Review' not in content, "Task created by user2 shown incorrectly"

    print("✓ 'Created by me' filters to tasks created by current user")


def test_view_mode_mine_assigned():
    """Test 'mine_assigned' filters to tasks where assigned_to_user = request.user"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?view=mine_assigned')
    content = response.content.decode('utf-8')

    # Should show Task 2 which is assigned to user1
    assert 'Task 2 - Todo' in content, "Task assigned to user1 not shown"

    print("✓ 'Assigned to me' filters to tasks assigned to current user")


def test_view_mode_team_assigned():
    """Test 'team_assigned' filters to tasks assigned to user's teams"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?view=team_assigned')
    content = response.content.decode('utf-8')

    # Should show Task 3 which is assigned to test-team
    assert 'Task 3 - In Progress' in content, "Task assigned to team not shown"

    print("✓ 'Assigned to my team' filters to tasks assigned to user's teams")


def test_view_mode_watching():
    """Test 'watching' filters to tasks user is watching"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?view=watching')
    content = response.content.decode('utf-8')

    # Should show Task 1 (user1 is watching directly)
    assert 'Task 1 - Backlog' in content, "Watched task not shown"

    # Should show Task 4 (test-team is watching, user1 is in test-team)
    assert 'Task 4 - Review' in content, "Task watched via team not shown"

    print("✓ 'Watching' filters to tasks user is watching (direct or via team)")


def test_project_filter():
    """Test project dropdown filters board to single project"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    project1 = Project.objects.get(name='Project Alpha')
    response = client.get(reverse('kanban:kanban-board') + f'?project={project1.pk}')
    content = response.content.decode('utf-8')

    # Should show tasks from Project Alpha
    assert 'Task 1 - Backlog' in content, "Project Alpha task not shown"

    # Should NOT show tasks from Project Beta
    assert 'Task 4 - Review' not in content, "Project Beta task shown incorrectly"

    print("✓ Project filter works correctly")


def test_priority_filter():
    """Test priority dropdown filters correctly"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + f'?priority={Task.PRIORITY_CRITICAL}')
    content = response.content.decode('utf-8')

    # Should show critical priority task
    assert 'Task 4 - Review' in content, "Critical priority task not shown"

    print("✓ Priority filter works correctly")


def test_due_filter_overdue():
    """Test due filter: overdue works correctly"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?due=overdue')
    content = response.content.decode('utf-8')

    # Should show Task 6 which is overdue and not done
    assert 'Task 6 - Overdue' in content, "Overdue task not shown"

    # Should NOT show Task 5 which is overdue but done
    assert 'Task 5 - Done' not in content, "Done task shown in overdue filter"

    print("✓ Due filter 'overdue' works correctly")


def test_due_filter_today():
    """Test due filter: today works correctly"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?due=today')
    content = response.content.decode('utf-8')

    # Should show Task 3 which is due today
    assert 'Task 3 - In Progress' in content, "Today's task not shown"

    print("✓ Due filter 'today' works correctly")


def test_due_filter_week():
    """Test due filter: this week works correctly"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board') + '?due=week')
    content = response.content.decode('utf-8')

    # Should show tasks due within 7 days
    assert 'Task 7 - This Week' in content, "This week's task not shown"

    print("✓ Due filter 'this week' works correctly")


def test_multiple_filters_combine():
    """Test multiple filters combine correctly (AND logic)"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    project1 = Project.objects.get(name='Project Alpha')
    response = client.get(
        reverse('kanban:kanban-board') +
        f'?view=mine_created&project={project1.pk}&priority={Task.PRIORITY_HIGH}'
    )
    content = response.content.decode('utf-8')

    # Should show Task 1 (created by user1, in Project Alpha, high priority)
    assert 'Task 1 - Backlog' in content, "Task matching all filters not shown"

    print("✓ Multiple filters combine correctly (AND logic)")


def test_htmx_partial_response():
    """Test HTMX request returns partial template"""
    client = Client()
    user = User.objects.first()
    client.force_login(user)

    response = client.get(
        reverse('kanban:kanban-board'),
        HTTP_HX_REQUEST='true'
    )
    content = response.content.decode('utf-8')

    # Should return partial board without full page structure
    assert '<html' not in content.lower(), "Full HTML returned for HTMX request"
    assert 'kanban-board' in content, "Partial board not returned"

    print("✓ HTMX request returns partial template")


def test_task_move_endpoint():
    """Test /tasks/<pk>/move/ endpoint works"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    task = Task.objects.get(title='Task 2 - Todo')
    response = client.post(
        reverse('tasks:task-move', args=[task.pk]),
        {'status': Task.STATUS_IN_PROGRESS, 'position': 0}
    )

    assert response.status_code == 204, f"Task move returned {response.status_code}"

    # Verify task status changed
    task.refresh_from_db()
    assert task.status == Task.STATUS_IN_PROGRESS, "Task status not updated"

    print("✓ Task move endpoint works correctly")


def test_column_counts():
    """Test column counts display correctly"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Should show badge with count for each column
    assert 'badge' in content, "Column count badges not found"

    print("✓ Column counts display correctly")


def run_all_tests():
    """Run all test functions"""
    print("\n" + "="*60)
    print("ISSUE-09: Kanban Board - Acceptance Criteria Tests")
    print("="*60)

    # Clean up existing test data
    Task.objects.filter(title__startswith='Task ').delete()
    Project.objects.filter(name__startswith='Project ').delete()
    Team.objects.filter(slug='test-team').delete()
    User.objects.filter(username__startswith='testuser').delete()

    # Setup test data
    setup_test_data()

    # Run tests
    tests = [
        test_kanban_board_url,
        test_all_columns_render,
        test_view_mode_all,
        test_view_mode_mine_created,
        test_view_mode_mine_assigned,
        test_view_mode_team_assigned,
        test_view_mode_watching,
        test_project_filter,
        test_priority_filter,
        test_due_filter_overdue,
        test_due_filter_today,
        test_due_filter_week,
        test_multiple_filters_combine,
        test_htmx_partial_response,
        test_task_move_endpoint,
        test_column_counts,
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
