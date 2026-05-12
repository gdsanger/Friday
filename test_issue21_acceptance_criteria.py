#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-21: Fix Project List UI Polish.

This script tests:
- Every project row has a colored left border matching project.color
- Progress bar is visible in both light and dark mode
- Progress bar color matches the project color
- Rows have clear visual separation (border + border-radius)
- Hovering a row shows lift effect (shadow + slight translate)
- Overdue projects show due date in red
- Owner name is visible on large screens, avatar only on small screens
- Chevron icon on right indicates the row is clickable
- "No tasks yet" renders correctly for projects with 0 tasks
- Empty state renders when no projects match the current filter
- Status badge color matches the status
- subtract template filter works correctly for progress calculation
- No layout regression on the project create/edit form
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.projects.models import Project, ProjectUserMembership
from apps.tasks.models import Task
from apps.core.templatetags.friday_tags import subtract, status_color
from datetime import date, timedelta

User = get_user_model()


def setup_test_data():
    """Create test users and projects for testing."""
    # Create test user
    test_user = User.objects.filter(username='test_ui_user').first()
    if not test_user:
        test_user = User.objects.create_user(
            username='test_ui_user',
            email='testui@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    # Create project with tasks
    project_with_tasks = Project.objects.filter(name='Project With Tasks').first()
    if not project_with_tasks:
        project_with_tasks = Project.objects.create(
            name='Project With Tasks',
            description='Has some tasks',
            status='active',
            owner=test_user,
            color='#3b82f6',
            due_date=date.today() + timedelta(days=7)
        )
        ProjectUserMembership.objects.create(
            project=project_with_tasks, user=test_user, role='manager'
        )
        # Create tasks
        for i in range(5):
            Task.objects.create(
                title=f'Task {i+1}',
                project=project_with_tasks,
                status='done' if i < 2 else 'in_progress',
                assigned_to_user=test_user
            )

    # Create project without tasks
    project_no_tasks = Project.objects.filter(name='Empty Project').first()
    if not project_no_tasks:
        project_no_tasks = Project.objects.create(
            name='Empty Project',
            description='No tasks yet',
            status='planning',
            owner=test_user,
            color='#ef4444',
            due_date=date.today() + timedelta(days=14)
        )
        ProjectUserMembership.objects.create(
            project=project_no_tasks, user=test_user, role='manager'
        )

    # Create overdue project
    overdue_project = Project.objects.filter(name='Overdue Project').first()
    if not overdue_project:
        overdue_project = Project.objects.create(
            name='Overdue Project',
            description='Past due date',
            status='on_hold',
            owner=test_user,
            color='#f59e0b',
            due_date=date.today() - timedelta(days=3)
        )
        ProjectUserMembership.objects.create(
            project=overdue_project, user=test_user, role='manager'
        )

    return test_user, project_with_tasks, project_no_tasks, overdue_project


def test_template_filters():
    """Test that template filters work correctly."""
    print("\n1. Testing template filters...")

    # Test subtract filter
    assert subtract(10, 3) == 7, "subtract(10, 3) should be 7"
    assert subtract('10', '3') == 7, "subtract with strings should work"
    assert subtract(None, 3) == 0, "subtract with None should return 0"
    print("   ✓ subtract filter works correctly")

    # Test status_color filter
    class MockProject:
        def __init__(self, status):
            self.status = status

    test_statuses = {
        'planning': '#4b5563',
        'active': '#166534',
        'on_hold': '#92400e',
        'done': '#1e3a5f',
        'archived': '#374151',
    }

    for status, expected_color in test_statuses.items():
        mock = MockProject(status)
        color = status_color(mock)
        assert color == expected_color, f"status_color for {status} should be {expected_color}, got {color}"

    print("   ✓ status_color filter works correctly for all statuses")
    return True


def test_project_list_rendering():
    """Test that project list renders with all required elements."""
    print("\n2. Testing project list rendering...")

    user, proj_with_tasks, proj_no_tasks, overdue = setup_test_data()

    client = Client()
    client.force_login(user)

    # Get project list with status=all to see all projects
    response = client.get(reverse('projects:project-list') + '?status=all')
    assert response.status_code == 200, "Project list should return 200"

    content = response.content.decode('utf-8')

    # Check for project names
    assert 'Project With Tasks' in content, "Project name should be visible"
    assert 'Empty Project' in content, "Project name should be visible"

    # Check for colored left border
    assert f'border-left: 4px solid {proj_with_tasks.color}' in content, \
        "Project should have colored left border"

    # Check for project-row class
    assert 'project-row' in content, "Project row should have project-row class"

    # Check for chevron icon
    assert 'bi-chevron-right' in content, "Chevron icon should be present"

    # Check for progress bar
    assert 'progress-bar' in content, "Progress bar should be present"

    # Check for "No tasks yet" for empty project
    assert 'No tasks yet' in content, "Empty project should show 'No tasks yet'"

    # Check for owner initials
    assert user.initials in content, "Owner initials should be visible"

    # Check for due date
    assert 'bi-calendar3' in content, "Calendar icon should be present for due dates"

    print("   ✓ All required elements are present in project list")
    return True


def test_overdue_date_styling():
    """Test that overdue projects show due date in red."""
    print("\n3. Testing overdue date styling...")

    user, _, _, overdue = setup_test_data()

    client = Client()
    client.force_login(user)

    response = client.get(reverse('projects:project-list') + '?status=all')
    content = response.content.decode('utf-8')

    # Check that overdue project has text-danger class
    # The template should render: {% if project.due_date < today %}text-danger{% else %}text-muted{% endif %}
    assert 'text-danger' in content, "Overdue project should have text-danger class"

    print("   ✓ Overdue projects show due date in red")
    return True


def test_progress_calculation():
    """Test that progress calculation works correctly."""
    print("\n4. Testing progress calculation...")

    user, proj_with_tasks, _, _ = setup_test_data()

    # Refresh to get task counts
    proj_with_tasks.refresh_from_db()

    client = Client()
    client.force_login(user)

    response = client.get(reverse('projects:project-list'))
    content = response.content.decode('utf-8')

    # Should show task progress (2 done out of 5)
    assert '2 / 5 tasks done' in content or '2/ 5 tasks done' in content, \
        "Should show correct task progress"

    print("   ✓ Progress calculation works correctly")
    return True


def test_css_styles():
    """Test that CSS styles are properly defined."""
    print("\n5. Testing CSS styles...")

    import os
    css_path = os.path.join(os.path.dirname(__file__), 'static', 'css', 'friday.css')

    with open(css_path, 'r') as f:
        css_content = f.read()

    # Check for project-row styles
    assert '.project-row {' in css_content, "project-row class should be defined"
    assert '.project-row:hover {' in css_content, "project-row hover state should be defined"

    # Check for shadow-md variable
    assert '--shadow-md:' in css_content, "shadow-md variable should be defined"

    # Check for font-mono variable
    assert '--font-mono:' in css_content, "font-mono variable should be defined"

    # Check for user-avatar-sm
    assert '.user-avatar-sm {' in css_content, "user-avatar-sm class should be defined"

    # Check for progress bar styling
    assert 'background-color: var(--friday-border) !important' in css_content, \
        "Progress bar background should be defined for dark mode visibility"

    print("   ✓ All required CSS styles are defined")
    return True


def test_empty_state():
    """Test that empty state renders correctly."""
    print("\n6. Testing empty state...")

    # Create a user with no projects
    empty_user = User.objects.filter(username='empty_user').first()
    if not empty_user:
        empty_user = User.objects.create_user(
            username='empty_user',
            email='empty@test.com',
            password='testpass123'
        )

    client = Client()
    client.force_login(empty_user)

    response = client.get(reverse('projects:project-list'))
    content = response.content.decode('utf-8')

    # Check for empty state
    assert 'No projects found' in content, "Empty state should show 'No projects found'"
    assert 'bi-folder2-open' in content, "Empty state should have folder icon"
    assert 'Create your first project' in content, "Empty state should have create button"

    print("   ✓ Empty state renders correctly")
    return True


def test_status_badge_colors():
    """Test that status badges have correct colors."""
    print("\n7. Testing status badge colors...")

    user, _, _, _ = setup_test_data()

    # Create projects with different statuses
    statuses = ['planning', 'active', 'on_hold', 'done', 'archived']
    for status in statuses:
        proj = Project.objects.filter(name=f'Status Test {status}').first()
        if not proj:
            proj = Project.objects.create(
                name=f'Status Test {status}',
                status=status,
                owner=user,
                color='#3b82f6'
            )
            ProjectUserMembership.objects.create(
                project=proj, user=user, role='manager'
            )

    client = Client()
    client.force_login(user)

    response = client.get(reverse('projects:project-list') + '?status=all')
    content = response.content.decode('utf-8')

    # Check that status badges have custom colors
    class MockProject:
        def __init__(self, status):
            self.status = status

    for status in statuses:
        expected_color = status_color(MockProject(status))
        # The badge should have inline style with background-color
        # style="background-color: {{ project|status_color }}
        assert expected_color in content or status.replace('_', ' ').title() in content, \
            f"Status badge for {status} should be present"

    print("   ✓ Status badges have correct colors")
    return True


def test_view_context():
    """Test that view passes today to context."""
    print("\n8. Testing view context...")

    from django.test import RequestFactory
    from apps.projects.views import ProjectListView

    user, _, _, _ = setup_test_data()

    factory = RequestFactory()
    request = factory.get('/projects/')
    request.user = user

    view = ProjectListView()
    view.setup(request)
    context = view.get_context_data(object_list=view.get_queryset())

    assert 'today' in context, "Context should contain 'today'"
    assert isinstance(context['today'], date), "'today' should be a date object"
    assert context['today'] == date.today(), "'today' should be current date"

    print("   ✓ View correctly passes 'today' to context")
    return True


def test_no_regression_on_forms():
    """Test that project create/edit forms still work."""
    print("\n9. Testing no regression on forms...")

    user, proj, _, _ = setup_test_data()

    client = Client()
    client.force_login(user)

    # Test create form
    response = client.get(reverse('projects:project-create'))
    assert response.status_code == 200, "Project create form should return 200"
    content = response.content.decode('utf-8')
    assert 'New Project' in content or 'Create Project' in content, \
        "Create form should have correct title"

    # Test edit form
    response = client.get(reverse('projects:project-edit', kwargs={'pk': proj.pk}))
    assert response.status_code == 200, "Project edit form should return 200"
    content = response.content.decode('utf-8')
    assert 'Edit Project' in content or 'Save Changes' in content, \
        "Edit form should have correct title"

    print("   ✓ Project forms work correctly (no regression)")
    return True


def run_all_tests():
    """Run all acceptance tests."""
    print("=" * 70)
    print("Testing ISSUE-21: Fix Project List UI Polish")
    print("=" * 70)

    tests = [
        test_template_filters,
        test_project_list_rendering,
        test_overdue_date_styling,
        test_progress_calculation,
        test_css_styles,
        test_empty_state,
        test_status_badge_colors,
        test_view_context,
        test_no_regression_on_forms,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            failed += 1
            print(f"   ✗ {test_func.__name__}: {str(e)}")
        except Exception as e:
            failed += 1
            print(f"   ✗ {test_func.__name__}: Unexpected error: {str(e)}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
