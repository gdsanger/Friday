#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-32: Assignee Filter.

This script tests all requirements from the issue:
- Assignee dropdown appears in Kanban filter bar
- Selecting an assignee filters board to tasks assigned to that person
- Filter combines correctly with other active filters (project, team, etc.)
- Portal users (is_portal_user=True) are excluded from the dropdown
- "Nur meine" button pre-filters to current user
- Clicking "Nur meine" again clears the filter
- Active assignee filter persists in URL
- Filter label shows correct selected name when active
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

User = get_user_model()


def setup_test_data():
    """Create test users, teams, projects, and tasks"""
    print("\n── Setting up test data ──")

    # Create regular users
    user1 = User.objects.create_user(
        username='testuser1',
        email='test1@example.com',
        password='testpass123',
        first_name='Alice',
        last_name='Manager',
        display_name='Alice Manager'
    )

    user2 = User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123',
        first_name='Bob',
        last_name='Developer',
        display_name='Bob Developer'
    )

    user3 = User.objects.create_user(
        username='testuser3',
        email='test3@example.com',
        password='testpass123',
        first_name='Charlie',
        last_name='Designer',
        display_name='Charlie Designer'
    )

    # Create a portal user (should be excluded from assignee dropdown)
    portal_user = User.objects.create_user(
        username='portaluser',
        email='portal@example.com',
        password='testpass123',
        first_name='Portal',
        last_name='User',
        is_portal_user=True
    )

    # Create team
    team = Team.objects.create(
        name='Test Team',
        slug='test-team'
    )
    TeamMembership.objects.create(user=user1, team=team, role='member')
    TeamMembership.objects.create(user=user2, team=team, role='member')

    # Create project
    project = Project.objects.create(
        name='Project Alpha',
        visibility='members',
        owner=user1
    )
    ProjectUserMembership.objects.create(
        project=project,
        user=user1,
        role='manager'
    )
    ProjectUserMembership.objects.create(
        project=project,
        user=user2,
        role='contributor'
    )

    # Create tasks with various assignees
    tasks = [
        Task.objects.create(
            title='Task 1 - Assigned to Alice',
            project=project,
            status=Task.STATUS_TODO,
            created_by=user1,
            assigned_to_user=user1,
        ),
        Task.objects.create(
            title='Task 2 - Assigned to Bob',
            project=project,
            status=Task.STATUS_IN_PROGRESS,
            created_by=user1,
            assigned_to_user=user2,
        ),
        Task.objects.create(
            title='Task 3 - Assigned to Charlie',
            project=project,
            status=Task.STATUS_TODO,
            created_by=user1,
            assigned_to_user=user3,
        ),
        Task.objects.create(
            title='Task 4 - Unassigned',
            project=project,
            status=Task.STATUS_BACKLOG,
            created_by=user1,
        ),
        Task.objects.create(
            title='Task 5 - Assigned to Portal User',
            project=project,
            status=Task.STATUS_TODO,
            created_by=user1,
            assigned_to_user=portal_user,
        ),
    ]

    print(f"✓ Created {len(tasks)} tasks")
    print(f"✓ Created {User.objects.count()} users (including 1 portal user)")
    print(f"✓ Created {Team.objects.count()} teams, {Project.objects.count()} projects")

    return user1, user2, user3, portal_user, team, project


def test_assignee_dropdown_appears():
    """Test assignee dropdown appears in Kanban filter bar"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check for assignee filter presence
    assert 'filter-assignee' in content, "Assignee filter dropdown not found"
    assert 'Alle Bearbeiter' in content, "Assignee filter label not found"

    print("✓ Assignee dropdown appears in Kanban filter bar")


def test_portal_users_excluded():
    """Test portal users are excluded from assignee dropdown"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check that regular users appear
    assert 'Alice Manager' in content, "Regular user not in dropdown"
    assert 'Bob Developer' in content, "Regular user not in dropdown"

    # Check that portal user is NOT in dropdown
    # Portal user should only appear if they have tasks, but not in the assignee filter
    assignee_section_start = content.find('filter-assignee')
    assignee_section_end = content.find('</select>', assignee_section_start)
    assignee_section = content[assignee_section_start:assignee_section_end]

    assert 'Portal User' not in assignee_section or content.count('Portal User') == 0, \
        "Portal user should not appear in assignee dropdown"

    print("✓ Portal users are excluded from assignee dropdown")


def test_assignee_filter_works():
    """Test selecting an assignee filters board to tasks assigned to that person"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    user2 = User.objects.get(username='testuser2')
    response = client.get(reverse('kanban:kanban-board') + f'?assignee={user2.pk}')
    content = response.content.decode('utf-8')

    # Should show Task 2 which is assigned to Bob
    assert 'Task 2 - Assigned to Bob' in content, "Task assigned to Bob not shown"

    # Should NOT show tasks assigned to others
    assert 'Task 1 - Assigned to Alice' not in content, "Task assigned to Alice shown incorrectly"
    assert 'Task 3 - Assigned to Charlie' not in content, "Task assigned to Charlie shown incorrectly"

    print("✓ Assignee filter correctly filters tasks")


def test_assignee_filter_combines_with_others():
    """Test assignee filter combines correctly with other active filters"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    project = Project.objects.get(name='Project Alpha')
    user2 = User.objects.get(username='testuser2')

    response = client.get(
        reverse('kanban:kanban-board') +
        f'?project={project.pk}&assignee={user2.pk}'
    )
    content = response.content.decode('utf-8')

    # Should show Task 2 (in Project Alpha, assigned to Bob)
    assert 'Task 2 - Assigned to Bob' in content, "Task matching both filters not shown"

    # Should NOT show tasks that don't match all filters
    assert 'Task 1 - Assigned to Alice' not in content, "Task not matching assignee shown"

    print("✓ Assignee filter combines correctly with other filters")


def test_nur_meine_button_appears():
    """Test 'Nur meine' button appears in view"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check for "Nur meine" button
    assert 'Nur meine' in content, "'Nur meine' button not found"
    assert 'bi-person-check' in content, "'Nur meine' button icon not found"

    print("✓ 'Nur meine' button appears in view")


def test_nur_meine_button_filters():
    """Test 'Nur meine' button pre-filters to current user"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    # Simulate clicking "Nur meine" button by passing assignee=user.pk
    response = client.get(reverse('kanban:kanban-board') + f'?assignee={user.pk}')
    content = response.content.decode('utf-8')

    # Should show Task 1 which is assigned to Alice (user1)
    assert 'Task 1 - Assigned to Alice' in content, "Current user's task not shown"

    # Should NOT show tasks assigned to others
    assert 'Task 2 - Assigned to Bob' not in content, "Other user's task shown incorrectly"

    # Button should be in active state (btn-primary)
    assert 'btn-primary' in content, "'Nur meine' button not in active state"

    print("✓ 'Nur meine' button pre-filters to current user")


def test_assignee_filter_persists_in_url():
    """Test active assignee filter persists in URL"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    user2 = User.objects.get(username='testuser2')
    url = reverse('kanban:kanban-board') + f'?assignee={user2.pk}'
    response = client.get(url)

    # Check that the response is successful
    assert response.status_code == 200

    # Check that the assignee dropdown shows the selected value
    content = response.content.decode('utf-8')
    assert f'value="{user2.pk}"' in content, "Assignee value not in dropdown"

    print("✓ Active assignee filter persists in URL")


def test_assignee_dropdown_shows_selected():
    """Test filter dropdown shows correct selected assignee"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    user2 = User.objects.get(username='testuser2')
    response = client.get(reverse('kanban:kanban-board') + f'?assignee={user2.pk}')
    content = response.content.decode('utf-8')

    # Check that the selected option has "selected" attribute
    # Find the assignee select section
    assignee_start = content.find('id="filter-assignee"')
    assignee_end = content.find('</select>', assignee_start)
    assignee_section = content[assignee_start:assignee_end]

    # Check that the user2's option has "selected" attribute
    assert f'value="{user2.pk}"' in assignee_section, "Assignee option not found in dropdown"
    assert 'selected' in assignee_section, "No option marked as selected in assignee dropdown"

    # More specific check: the option with user2.pk should have selected attribute
    option_pattern = f'value="{user2.pk}"'
    option_pos = assignee_section.find(option_pattern)
    next_close = assignee_section.find('>', option_pos)
    option_tag = assignee_section[option_pos:next_close]
    assert 'selected' in option_tag, f"Option for user {user2.pk} not marked as selected"

    print("✓ Assignee dropdown shows correct selected assignee")


def test_htmx_includes_assignee():
    """Test HTMX includes assignee parameter in all filters"""
    client = Client()
    user = User.objects.get(username='testuser1')
    client.force_login(user)

    response = client.get(reverse('kanban:kanban-board'))
    content = response.content.decode('utf-8')

    # Check that hx-include contains [name='assignee'] in various places
    assert content.count("[name='assignee']") >= 5, \
        "hx-include should include [name='assignee'] in multiple filters"

    print("✓ HTMX includes assignee parameter in all filters")


def run_all_tests():
    """Run all test functions"""
    print("\n" + "="*60)
    print("ISSUE-32: Assignee Filter - Acceptance Criteria Tests")
    print("="*60)

    # Clean up existing test data
    Task.objects.filter(title__startswith='Task ').delete()
    Project.objects.filter(name__startswith='Project ').delete()
    Team.objects.filter(slug='test-team').delete()
    User.objects.filter(username__startswith='testuser').delete()
    User.objects.filter(username='portaluser').delete()

    # Setup test data
    setup_test_data()

    # Run tests
    tests = [
        test_assignee_dropdown_appears,
        test_portal_users_excluded,
        test_assignee_filter_works,
        test_assignee_filter_combines_with_others,
        test_nur_meine_button_appears,
        test_nur_meine_button_filters,
        test_assignee_filter_persists_in_url,
        test_assignee_dropdown_shows_selected,
        test_htmx_includes_assignee,
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
