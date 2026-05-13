#!/usr/bin/env python
"""
Test script to verify ISSUE-45: Calendar Filter Bar implementation.

This script tests:
- CalendarDataView returns filter_options in JSON response
- filter_options includes projects, teams, users, and clients
- Task and project data includes filter fields (project_id, team_id, user_id, client_id)
- Filter options are populated from actual task assignments
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
from apps.core.models import Client as ClientModel
from datetime import date, timedelta
import json

User = get_user_model()


def setup_test_data():
    """Create test users, projects, teams, clients and tasks for filter testing"""
    print("\n── Setting up test data ──")

    # Clean up existing test data
    User.objects.filter(username__startswith='testuser_filter').delete()
    Team.objects.filter(slug__startswith='test-team-filter').delete()
    Project.objects.filter(name__startswith='Test Filter Project').delete()
    ClientModel.objects.filter(name__startswith='Test Filter Client').delete()

    # Create clients
    client1 = ClientModel.objects.create(
        name='Test Filter Client Alpha',
        slug='test-filter-client-alpha',
        color='#3b82f6'
    )

    client2 = ClientModel.objects.create(
        name='Test Filter Client Beta',
        slug='test-filter-client-beta',
        color='#10b981'
    )

    # Create users
    user1 = User.objects.create_user(
        username='testuser_filter_1',
        email='filter1@example.com',
        password='testpass123',
        first_name='Filter',
        last_name='User1'
    )

    user2 = User.objects.create_user(
        username='testuser_filter_2',
        email='filter2@example.com',
        password='testpass123',
        first_name='Filter',
        last_name='User2'
    )

    # Create teams
    team1 = Team.objects.create(
        name='Test Filter Team Alpha',
        slug='test-team-filter-alpha',
        color='#ef4444'
    )
    TeamMembership.objects.create(user=user1, team=team1, role='member')

    team2 = Team.objects.create(
        name='Test Filter Team Beta',
        slug='test-team-filter-beta',
        color='#f59e0b'
    )
    TeamMembership.objects.create(user=user2, team=team2, role='member')

    # Create projects with clients
    today = date.today()
    project1 = Project.objects.create(
        name='Test Filter Project Alpha',
        visibility='members',
        owner=user1,
        client=client1,
        color='#3b82f6',
        start_date=today,
        due_date=today + timedelta(days=30)
    )
    ProjectUserMembership.objects.create(
        project=project1,
        user=user1,
        role='manager'
    )

    project2 = Project.objects.create(
        name='Test Filter Project Beta',
        visibility='members',
        owner=user2,
        client=client2,
        color='#10b981',
        start_date=today + timedelta(days=10),
        due_date=today + timedelta(days=60)
    )
    ProjectUserMembership.objects.create(
        project=project2,
        user=user1,
        role='contributor'
    )
    ProjectUserMembership.objects.create(
        project=project2,
        user=user2,
        role='manager'
    )

    # Create tasks with various assignments
    task1 = Task.objects.create(
        title='Task assigned to user1',
        project=project1,
        status='todo',
        priority=2,
        created_by=user1,
        assigned_to_user=user1,
        deadline=today + timedelta(days=10)
    )

    task2 = Task.objects.create(
        title='Task assigned to team1',
        project=project1,
        status='in_progress',
        priority=3,
        created_by=user1,
        assigned_to_team=team1,
        deadline=today + timedelta(days=15)
    )

    task3 = Task.objects.create(
        title='Task assigned to user2',
        project=project2,
        status='todo',
        priority=2,
        created_by=user2,
        assigned_to_user=user2,
        deadline=today + timedelta(days=20)
    )

    task4 = Task.objects.create(
        title='Task assigned to team2',
        project=project2,
        status='review',
        priority=3,
        created_by=user2,
        assigned_to_team=team2,
        deadline=today + timedelta(days=25)
    )

    print(f"  ✓ Created client1: {client1.name}")
    print(f"  ✓ Created client2: {client2.name}")
    print(f"  ✓ Created user1: {user1.username}")
    print(f"  ✓ Created user2: {user2.username}")
    print(f"  ✓ Created team1: {team1.name}")
    print(f"  ✓ Created team2: {team2.name}")
    print(f"  ✓ Created project1: {project1.name} (client: {client1.name})")
    print(f"  ✓ Created project2: {project2.name} (client: {client2.name})")
    print(f"  ✓ Created 4 tasks with various assignments")

    return {
        'user1': user1,
        'user2': user2,
        'team1': team1,
        'team2': team2,
        'client1': client1,
        'client2': client2,
        'project1': project1,
        'project2': project2,
        'task1': task1,
        'task2': task2,
        'task3': task3,
        'task4': task4,
    }


def test_calendar_data_has_filter_options(data):
    """Test that calendar data endpoint returns filter_options"""
    print("\n── Test 1: Calendar data includes filter_options ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar-data')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    data_json = response.json()

    # Check filter_options exists
    assert 'filter_options' in data_json, "Response should have 'filter_options' key"
    print("  ✓ JSON has 'filter_options' key")

    filter_options = data_json['filter_options']

    # Check structure
    assert 'projects' in filter_options, "filter_options should have 'projects'"
    assert 'teams' in filter_options, "filter_options should have 'teams'"
    assert 'users' in filter_options, "filter_options should have 'users'"
    assert 'clients' in filter_options, "filter_options should have 'clients'"
    print("  ✓ filter_options has all required keys (projects, teams, users, clients)")

    print("  ✅ PASSED: Calendar data includes filter_options")


def test_filter_options_content(data):
    """Test that filter_options contain correct data"""
    print("\n── Test 2: Filter options contain correct data ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar-data')
    response = client.get(url)
    data_json = response.json()
    filter_options = data_json['filter_options']

    # Check projects
    projects = filter_options['projects']
    assert len(projects) >= 2, f"Should have at least 2 projects, got {len(projects)}"
    print(f"  ✓ Found {len(projects)} projects in filter options")

    project_names = [p['name'] for p in projects]
    assert data['project1'].name in project_names, "Project1 should be in filter options"
    assert data['project2'].name in project_names, "Project2 should be in filter options"
    print("  ✓ Projects have correct names")

    # Check teams
    teams = filter_options['teams']
    assert len(teams) >= 2, f"Should have at least 2 teams, got {len(teams)}"
    print(f"  ✓ Found {len(teams)} teams in filter options")

    team_names = [t['name'] for t in teams]
    assert data['team1'].name in team_names, "Team1 should be in filter options"
    assert data['team2'].name in team_names, "Team2 should be in filter options"
    print("  ✓ Teams have correct names")

    # Check users
    users = filter_options['users']
    assert len(users) >= 2, f"Should have at least 2 users, got {len(users)}"
    print(f"  ✓ Found {len(users)} users in filter options")

    user_names = [u['name'] for u in users]
    assert data['user1'].full_name in user_names, "User1 should be in filter options"
    assert data['user2'].full_name in user_names, "User2 should be in filter options"
    print("  ✓ Users have correct names")

    # Check clients
    clients = filter_options['clients']
    assert len(clients) >= 2, f"Should have at least 2 clients, got {len(clients)}"
    print(f"  ✓ Found {len(clients)} clients in filter options")

    client_names = [c['name'] for c in clients]
    assert data['client1'].name in client_names, "Client1 should be in filter options"
    assert data['client2'].name in client_names, "Client2 should be in filter options"
    print("  ✓ Clients have correct names")

    print("  ✅ PASSED: Filter options contain correct data")


def test_task_data_has_filter_fields(data):
    """Test that task data includes filter fields"""
    print("\n── Test 3: Task data includes filter fields ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar-data')
    response = client.get(url)
    data_json = response.json()
    gantt_data = data_json['data']

    # Find a task item
    task_items = [item for item in gantt_data if item.get('type') in ['task', 'milestone']]
    assert len(task_items) >= 4, f"Should have at least 4 task items, got {len(task_items)}"
    print(f"  ✓ Found {len(task_items)} task items")

    # Check first task has all filter fields
    task_item = task_items[0]
    assert 'project_id' in task_item, "Task should have 'project_id' field"
    assert 'team_id' in task_item, "Task should have 'team_id' field"
    assert 'user_id' in task_item, "Task should have 'user_id' field"
    assert 'client_id' in task_item, "Task should have 'client_id' field"
    print("  ✓ Task items have all filter fields (project_id, team_id, user_id, client_id)")

    # Check that filter fields are strings (as required by JS comparison)
    assert isinstance(task_item['project_id'], str), "project_id should be a string"
    print("  ✓ Filter field IDs are strings")

    # Find task1 and verify its filter fields
    task1_item = next((item for item in task_items if item.get('task_id') == data['task1'].pk), None)
    assert task1_item is not None, "Task1 should be in data"
    assert task1_item['project_id'] == str(data['project1'].pk), "Task1 project_id should match"
    assert task1_item['user_id'] == str(data['user1'].pk), "Task1 user_id should match"
    assert task1_item['client_id'] == str(data['client1'].pk), "Task1 client_id should match"
    print("  ✓ Task1 filter fields have correct values")

    print("  ✅ PASSED: Task data includes correct filter fields")


def test_project_data_has_filter_fields(data):
    """Test that project bars include filter fields"""
    print("\n── Test 4: Project data includes filter fields ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar-data')
    response = client.get(url)
    data_json = response.json()
    gantt_data = data_json['data']

    # Find project items
    project_items = [item for item in gantt_data if item.get('type') == 'project']
    assert len(project_items) >= 2, f"Should have at least 2 project items, got {len(project_items)}"
    print(f"  ✓ Found {len(project_items)} project items")

    # Check first project has all filter fields
    project_item = project_items[0]
    assert 'project_id' in project_item, "Project should have 'project_id' field"
    assert 'team_id' in project_item, "Project should have 'team_id' field"
    assert 'user_id' in project_item, "Project should have 'user_id' field"
    assert 'client_id' in project_item, "Project should have 'client_id' field"
    print("  ✓ Project items have all filter fields")

    # Check that project bars have team_id and user_id set to None
    assert project_item['team_id'] is None, "Project bar team_id should be None"
    assert project_item['user_id'] is None, "Project bar user_id should be None"
    print("  ✓ Project bars have team_id and user_id set to None")

    # Find project1 and verify its filter fields
    project1_item = next((item for item in project_items if item['project_id'] == str(data['project1'].pk)), None)
    assert project1_item is not None, "Project1 should be in data"
    assert project1_item['client_id'] == str(data['client1'].pk), "Project1 client_id should match"
    print("  ✓ Project1 filter fields have correct values")

    print("  ✅ PASSED: Project data includes correct filter fields")


def test_filter_bar_html_exists(data):
    """Test that calendar view includes filter bar HTML"""
    print("\n── Test 5: Calendar view includes filter bar HTML ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    content = response.content.decode('utf-8')

    # Check for filter bar container
    assert 'calendar-filter-bar' in content, "Should have calendar-filter-bar div"
    print("  ✓ Filter bar container present")

    # Check for filter dropdowns
    assert 'filter-project' in content, "Should have project filter dropdown"
    assert 'filter-team' in content, "Should have team filter dropdown"
    assert 'filter-user' in content, "Should have user filter dropdown"
    assert 'filter-client' in content, "Should have client filter dropdown"
    print("  ✓ All four filter dropdowns present")

    # Check for reset button
    assert 'filter-reset-btn' in content, "Should have reset button"
    assert 'Zurücksetzen' in content, "Reset button should have German text"
    print("  ✓ Reset button present")

    # Check for active filter badges container
    assert 'active-filter-badges' in content, "Should have active filter badges container"
    print("  ✓ Active filter badges container present")

    print("  ✅ PASSED: Calendar view includes filter bar HTML")


def test_filter_javascript_functions(data):
    """Test that calendar view includes filter JavaScript functions"""
    print("\n── Test 6: Calendar view includes filter JavaScript ──")

    client = Client()
    client.force_login(data['user1'])

    url = reverse('projects:calendar')
    response = client.get(url)
    content = response.content.decode('utf-8')

    # Check for filter functions
    assert 'function populateFilterDropdowns' in content, "Should have populateFilterDropdowns function"
    assert 'function applyGanttFilters' in content, "Should have applyGanttFilters function"
    assert 'function resetGanttFilters' in content, "Should have resetGanttFilters function"
    assert 'function removeFilter' in content, "Should have removeFilter function"
    assert 'function updateFilterBadges' in content, "Should have updateFilterBadges function"
    assert 'function updateResetButton' in content, "Should have updateResetButton function"
    print("  ✓ All filter functions present")

    # Check for filter state object
    assert 'const _filters' in content, "Should have _filters state object"
    print("  ✓ Filter state object present")

    # Check for DHTMLX event attachment
    assert 'onBeforeTaskDisplay' in content, "Should attach onBeforeTaskDisplay event"
    print("  ✓ DHTMLX filter event attached")

    # Check for filter dropdown population call
    assert 'populateFilterDropdowns(data.filter_options)' in content, \
        "Should call populateFilterDropdowns with filter_options"
    print("  ✓ Filter dropdowns population call present")

    print("  ✅ PASSED: Calendar view includes filter JavaScript")


def run_all_tests():
    """Run all filter bar tests"""
    print("=" * 60)
    print("ISSUE-45: Calendar Filter Bar")
    print("Implementation Tests")
    print("=" * 60)

    data = setup_test_data()

    try:
        test_calendar_data_has_filter_options(data)
        test_filter_options_content(data)
        test_task_data_has_filter_fields(data)
        test_project_data_has_filter_fields(data)
        test_filter_bar_html_exists(data)
        test_filter_javascript_functions(data)

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
