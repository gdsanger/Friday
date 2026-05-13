#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-24: Project Calendar & Resource Gantt.

This script tests all requirements from the issue:
- Model: Task.deadline field exists and is nullable
- Calendar View: GET /projects/calendar/ renders Gantt chart
- Calendar Data: GET /projects/calendar/data/ returns JSON with projects and tasks
- Project bars render with correct dates and colors
- Task deadlines render as milestones
- Calendar Update: POST /projects/calendar/update/ saves project dates
- Permissions: Only managers and staff can update projects
- Task forms include deadline field
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
import json

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks with deadlines"""
    print("\n── Setting up test data ──")

    # Clean up existing test data
    User.objects.filter(username__startswith='testuser_cal').delete()
    Team.objects.filter(slug__startswith='test-team-cal').delete()
    Project.objects.filter(name__startswith='Test Calendar Project').delete()

    # Create users
    manager = User.objects.create_user(
        username='testuser_cal_manager',
        email='manager_cal@example.com',
        password='testpass123',
        first_name='Manager',
        last_name='User'
    )

    contributor = User.objects.create_user(
        username='testuser_cal_contributor',
        email='contributor_cal@example.com',
        password='testpass123',
        first_name='Contributor',
        last_name='User'
    )

    staff = User.objects.create_user(
        username='testuser_cal_staff',
        email='staff_cal@example.com',
        password='testpass123',
        first_name='Staff',
        last_name='User',
        is_staff=True
    )

    # Create team
    team = Team.objects.create(
        name='Test Calendar Team',
        slug='test-team-cal',
        color='#10b981'
    )
    TeamMembership.objects.create(user=contributor, team=team, role='member')

    # Create projects with dates
    today = date.today()
    project1 = Project.objects.create(
        name='Test Calendar Project Alpha',
        visibility='members',
        owner=manager,
        color='#3b82f6',
        start_date=today,
        due_date=today + timedelta(days=30)
    )
    ProjectUserMembership.objects.create(
        project=project1,
        user=manager,
        role='manager'
    )
    ProjectUserMembership.objects.create(
        project=project1,
        user=contributor,
        role='contributor'
    )

    project2 = Project.objects.create(
        name='Test Calendar Project Beta',
        visibility='members',
        owner=manager,
        color='#10b981',
        start_date=today + timedelta(days=10),
        due_date=today + timedelta(days=60)
    )
    ProjectUserMembership.objects.create(
        project=project2,
        user=manager,
        role='manager'
    )

    # Project without due_date (should not appear in calendar)
    project3 = Project.objects.create(
        name='Test Calendar Project No Date',
        visibility='members',
        owner=manager,
        color='#ef4444',
        start_date=today
    )
    ProjectUserMembership.objects.create(
        project=project3,
        user=manager,
        role='manager'
    )

    # Create tasks with deadlines
    task1 = Task.objects.create(
        title='Task with deadline 1',
        project=project1,
        status='todo',
        priority=3,
        created_by=manager,
        assigned_to_user=contributor,
        deadline=today + timedelta(days=15)
    )

    task2 = Task.objects.create(
        title='Task with deadline 2',
        project=project1,
        status='in_progress',
        priority=4,
        created_by=manager,
        assigned_to_team=team,
        deadline=today + timedelta(days=20)
    )

    # Task without deadline (should not appear as milestone)
    task3 = Task.objects.create(
        title='Task without deadline',
        project=project1,
        status='todo',
        priority=2,
        created_by=manager,
        due_date=today + timedelta(days=10)
    )

    print(f"  ✓ Created manager: {manager.username}")
    print(f"  ✓ Created contributor: {contributor.username}")
    print(f"  ✓ Created staff: {staff.username}")
    print(f"  ✓ Created team: {team.name}")
    print(f"  ✓ Created project1: {project1.name} (dates: {project1.start_date} to {project1.due_date})")
    print(f"  ✓ Created project2: {project2.name} (dates: {project2.start_date} to {project2.due_date})")
    print(f"  ✓ Created project3: {project3.name} (no due_date)")
    print(f"  ✓ Created task1 with deadline: {task1.title}")
    print(f"  ✓ Created task2 with deadline: {task2.title}")
    print(f"  ✓ Created task3 without deadline: {task3.title}")

    return {
        'manager': manager,
        'contributor': contributor,
        'staff': staff,
        'team': team,
        'project1': project1,
        'project2': project2,
        'project3': project3,
        'task1': task1,
        'task2': task2,
        'task3': task3,
    }


def test_model_deadline_field(data):
    """Test that Task.deadline field exists and works correctly"""
    print("\n── Test 1: Task.deadline field exists ──")

    task = data['task1']

    # Check field exists
    assert hasattr(task, 'deadline'), "Task model should have 'deadline' field"
    print("  ✓ Task.deadline field exists")

    # Check it's nullable
    assert task.deadline is not None, "Task should have a deadline"
    print(f"  ✓ Task deadline is set: {task.deadline}")

    # Check task without deadline
    task_no_deadline = data['task3']
    assert task_no_deadline.deadline is None, "Task3 should have no deadline"
    print("  ✓ Tasks can have NULL deadline")

    # Check we can update deadline
    new_deadline = date.today() + timedelta(days=25)
    task.deadline = new_deadline
    task.save()
    task.refresh_from_db()
    assert task.deadline == new_deadline, "Deadline should be updatable"
    print("  ✓ Deadline can be updated")

    print("  ✅ PASSED: Task.deadline field works correctly")


def test_calendar_view_renders(data):
    """Test that GET /projects/calendar/ renders successfully"""
    print("\n── Test 2: Calendar view renders ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('projects:calendar')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    content = response.content.decode('utf-8')

    # Check for DHTMLX Gantt library
    assert 'dhtmlxgantt.js' in content, "Should load DHTMLX Gantt JavaScript"
    assert 'dhtmlxgantt.css' in content, "Should load DHTMLX Gantt CSS"
    print("  ✓ DHTMLX Gantt library is loaded")

    # Check for gantt container
    assert 'gantt-container' in content, "Should have gantt-container div"
    print("  ✓ Gantt container div present")

    # Check for scale switcher buttons
    assert 'Month' in content and 'Quarter' in content and 'Year' in content, \
        "Should have scale switcher buttons"
    print("  ✓ Scale switcher buttons present")

    # Check for resource toggle button
    assert 'Resource View' in content, "Should have Resource View toggle"
    print("  ✓ Resource View toggle present")

    print("  ✅ PASSED: Calendar view renders correctly")


def test_calendar_data_endpoint(data):
    """Test that GET /projects/calendar/data/ returns correct JSON"""
    print("\n── Test 3: Calendar data endpoint ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('projects:calendar-data')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    data_json = response.json()

    # Check structure
    assert 'data' in data_json, "Response should have 'data' key"
    assert 'links' in data_json, "Response should have 'links' key"
    assert 'resources' in data_json, "Response should have 'resources' key"
    print("  ✓ JSON has correct structure (data, links, resources)")

    gantt_data = data_json['data']

    # Check projects appear
    project_items = [item for item in gantt_data if item.get('type') == 'project']
    assert len(project_items) >= 2, f"Should have at least 2 projects, got {len(project_items)}"
    print(f"  ✓ Found {len(project_items)} project bars")

    # Check project1 appears correctly
    project1_item = next((item for item in project_items if item['project_id'] == data['project1'].pk), None)
    assert project1_item is not None, "Project1 should appear in data"
    assert project1_item['text'] == data['project1'].name, "Project name should match"
    assert project1_item['color'] == data['project1'].color, "Project color should match"
    print(f"  ✓ Project1 '{project1_item['text']}' has correct name and color")

    # Check project3 (without due_date) does NOT appear
    project3_item = next((item for item in project_items if 'project_id' in item and item['project_id'] == data['project3'].pk), None)
    assert project3_item is None, "Project without due_date should not appear"
    print("  ✓ Projects without due_date are excluded")

    # Check task milestones appear
    milestone_items = [item for item in gantt_data if item.get('type') == 'milestone']
    assert len(milestone_items) >= 2, f"Should have at least 2 milestones, got {len(milestone_items)}"
    print(f"  ✓ Found {len(milestone_items)} task milestones")

    # Check task1 milestone
    task1_item = next((item for item in milestone_items if item.get('task_id') == data['task1'].pk), None)
    assert task1_item is not None, "Task1 should appear as milestone"
    assert task1_item['text'] == data['task1'].title, "Task title should match"
    assert task1_item['duration'] == 0, "Milestone should have duration 0"
    assert task1_item['parent'] == f"p_{data['project1'].pk}", "Milestone should be child of project"
    print(f"  ✓ Task1 milestone '{task1_item['text']}' is correctly configured")

    # Check resources
    resources = data_json['resources']
    assert len(resources) >= 2, f"Should have at least 2 resources, got {len(resources)}"
    print(f"  ✓ Found {len(resources)} resources (users/teams)")

    # Check user resource
    contributor_resource = next((r for r in resources if r['id'] == f"u_{data['contributor'].pk}"), None)
    assert contributor_resource is not None, "Contributor should appear as resource"
    print(f"  ✓ User resource '{contributor_resource['label']}' present")

    # Check team resource
    team_resource = next((r for r in resources if r['id'] == f"t_{data['team'].pk}"), None)
    assert team_resource is not None, "Team should appear as resource"
    print(f"  ✓ Team resource '{team_resource['label']}' present")

    print("  ✅ PASSED: Calendar data endpoint returns correct JSON")


def test_calendar_update_endpoint(data):
    """Test that POST /projects/calendar/update/ saves project dates"""
    print("\n── Test 4: Calendar update endpoint ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('projects:calendar-update')
    new_start = date.today() + timedelta(days=5)
    new_end = date.today() + timedelta(days=35)

    payload = {
        'type': 'project',
        'id': data['project1'].pk,
        'start_date': new_start.strftime('%d-%m-%Y'),
        'end_date': new_end.strftime('%d-%m-%Y'),
    }

    response = client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json'
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ POST {url} returns 200")

    # Check project dates were updated
    data['project1'].refresh_from_db()
    assert data['project1'].start_date == new_start, "Start date should be updated"
    assert data['project1'].due_date == new_end, "Due date should be updated"
    print(f"  ✓ Project dates updated: {data['project1'].start_date} to {data['project1'].due_date}")

    print("  ✅ PASSED: Calendar update saves project dates")


def test_calendar_update_permissions(data):
    """Test that only managers and staff can update projects"""
    print("\n── Test 5: Calendar update permissions ──")

    client = Client()
    url = reverse('projects:calendar-update')
    payload = {
        'type': 'project',
        'id': data['project1'].pk,
        'start_date': date.today().strftime('%d-%m-%Y'),
        'end_date': (date.today() + timedelta(days=30)).strftime('%d-%m-%Y'),
    }

    # Test contributor (should fail)
    client.force_login(data['contributor'])
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 403, f"Contributor should get 403, got {response.status_code}"
    print("  ✓ Contributor cannot update project dates (403)")

    # Test manager (should succeed)
    client.force_login(data['manager'])
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 200, f"Manager should get 200, got {response.status_code}"
    print("  ✓ Manager can update project dates (200)")

    # Test staff (should succeed)
    client.force_login(data['staff'])
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 200, f"Staff should get 200, got {response.status_code}"
    print("  ✓ Staff can update project dates (200)")

    print("  ✅ PASSED: Calendar update permissions work correctly")


def test_task_create_form_has_deadline(data):
    """Test that task creation form includes deadline field"""
    print("\n── Test 6: Task create form has deadline field ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('tasks:task-create')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    content = response.content.decode('utf-8')

    # Check for deadline input field
    assert 'name="deadline"' in content, "Form should have deadline input field"
    assert 'type="date"' in content, "Deadline should be a date input"
    print("  ✓ Deadline input field present in form")

    # Check for help text
    assert 'Hard deadline' in content or 'calendar' in content, \
        "Form should have help text about deadline"
    print("  ✓ Deadline field has descriptive help text")

    print("  ✅ PASSED: Task create form includes deadline field")


def test_task_creation_saves_deadline(data):
    """Test that task creation saves the deadline field"""
    print("\n── Test 7: Task creation saves deadline ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('tasks:task-create')
    deadline = date.today() + timedelta(days=14)

    response = client.post(url, {
        'title': 'New task with deadline',
        'project': data['project1'].pk,
        'status': 'todo',
        'priority': 2,
        'deadline': deadline.strftime('%Y-%m-%d'),
    })

    # Should redirect or return 200
    assert response.status_code in [200, 302], \
        f"Expected 200 or 302, got {response.status_code}"
    print(f"  ✓ POST {url} returns {response.status_code}")

    # Check task was created with deadline
    new_task = Task.objects.filter(title='New task with deadline').first()
    assert new_task is not None, "Task should be created"
    assert new_task.deadline == deadline, f"Deadline should be {deadline}, got {new_task.deadline}"
    print(f"  ✓ Task created with deadline: {new_task.deadline}")

    print("  ✅ PASSED: Task creation saves deadline field")


def test_task_slide_over_has_deadline(data):
    """Test that task slide-over includes deadline field"""
    print("\n── Test 8: Task slide-over has deadline field ──")

    client = Client()
    client.force_login(data['manager'])

    url = reverse('tasks:task-detail', kwargs={'pk': data['task1'].pk})
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    content = response.content.decode('utf-8')

    # Check for deadline field
    assert 'name="deadline"' in content, "Slide-over should have deadline field"
    print("  ✓ Deadline field present in slide-over")

    # Check deadline value is shown
    if data['task1'].deadline:
        deadline_str = data['task1'].deadline.strftime('%Y-%m-%d')
        assert deadline_str in content, f"Deadline value {deadline_str} should be shown"
        print(f"  ✓ Current deadline value displayed: {deadline_str}")

    print("  ✅ PASSED: Task slide-over includes deadline field")


def test_sidebar_calendar_link(data):
    """Test that sidebar includes Calendar link"""
    print("\n── Test 9: Sidebar has Calendar link ──")

    client = Client()
    client.force_login(data['manager'])

    # Get any page that includes the sidebar
    url = reverse('dashboard:dashboard')
    response = client.get(url)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ GET {url} returns 200")

    content = response.content.decode('utf-8')

    # Check for Calendar link in sidebar
    calendar_url = reverse('projects:calendar')
    assert calendar_url in content or '/projects/calendar/' in content, \
        "Sidebar should have Calendar link"
    print("  ✓ Calendar link present in sidebar")

    # Check for calendar icon
    assert 'bi-calendar3' in content, "Calendar link should have calendar icon"
    print("  ✓ Calendar icon present")

    print("  ✅ PASSED: Sidebar includes Calendar link")


def run_all_tests():
    """Run all acceptance criteria tests"""
    print("=" * 60)
    print("ISSUE-24: Project Calendar & Resource Gantt")
    print("Acceptance Criteria Tests")
    print("=" * 60)

    data = setup_test_data()

    try:
        test_model_deadline_field(data)
        test_calendar_view_renders(data)
        test_calendar_data_endpoint(data)
        test_calendar_update_endpoint(data)
        test_calendar_update_permissions(data)
        test_task_create_form_has_deadline(data)
        test_task_creation_saves_deadline(data)
        test_task_slide_over_has_deadline(data)
        test_sidebar_calendar_link(data)

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
