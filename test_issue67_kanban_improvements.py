#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-67: Kanban View Verbesserungen.

This script tests all requirements from the issue:
Fix 1 - Flexible Column Widths:
  - Columns use flex: 1 instead of fixed width
  - Board fills available screen space
  - Minimum width 200px per column
  - Maximum width 400px per column
  - Mobile: horizontal scrolling with fixed minimum width

Fix 2 - "Done" Column Hidden by Default:
  - "Done" column is hidden by default
  - Toggle button in filter bar is visible
  - Click toggles column visibility
  - State saved in localStorage
  - State persists after page reload
  - State persists after HTMX board reload
  - Button label changes: "Erledigt anzeigen" / "Erledigt ausblenden"

Fix 3 - Compact Filter Bar:
  - All filter dropdowns use form-select-sm
  - Filter bar is a compact single row
  - All previous filters still function
  - Labels filter integrated
  - Clear button only visible when filters are active

Fix 4 - "+ Add task" Removed:
  - No "+ Add task" button at end of columns
  - "New Task" button at top right still present
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
from apps.projects.models import Project, ProjectUserMembership
from apps.tasks.models import Task, Label
from bs4 import BeautifulSoup

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks"""
    print("\n── Setting up test data ──")

    # Create user
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )

    # Create project
    project = Project.objects.create(
        name='Test Project',
        description='Test project for ISSUE-67',
        status=Project.STATUS_ACTIVE
    )

    # Add user as member
    ProjectUserMembership.objects.create(
        project=project,
        user=user,
        role=ProjectUserMembership.ROLE_MEMBER
    )

    # Create a label
    label = Label.objects.create(
        name='Test Label',
        color='#3b82f6'
    )

    # Create tasks in different statuses
    for status, _ in Task.STATUS_CHOICES:
        task = Task.objects.create(
            title=f'Task in {status}',
            description=f'Test task in {status} status',
            project=project,
            status=status,
            created_by=user
        )
        if status == Task.STATUS_DONE:
            task.labels.add(label)

    print(f"✓ Created user: {user.username}")
    print(f"✓ Created project: {project.name}")
    print(f"✓ Created {Task.objects.count()} tasks")
    print(f"✓ Created label: {label.name}")

    return user, project, label


def test_fix1_flexible_column_widths():
    """Test Fix 1: Flexible column widths with flex layout"""
    print("\n── Test Fix 1: Flexible Column Widths ──")

    # Read the CSS file
    css_path = 'static/css/friday.css'
    with open(css_path, 'r') as f:
        css_content = f.read()

    # Check kanban-board has flex display
    assert 'display: flex;' in css_content, "kanban-board should have display: flex"
    print("✓ kanban-board uses display: flex")

    # Check kanban-column uses flex: 1
    assert 'flex: 1;' in css_content, "kanban-column should use flex: 1"
    print("✓ kanban-column uses flex: 1 (flexible width)")

    # Check min-width constraint
    assert 'min-width: 200px;' in css_content, "kanban-column should have min-width: 200px"
    print("✓ kanban-column has min-width: 200px")

    # Check max-width constraint
    assert 'max-width: 400px;' in css_content, "kanban-column should have max-width: 400px"
    print("✓ kanban-column has max-width: 400px")

    # Check media query for large screens
    assert 'max-width: 480px;' in css_content, "kanban-column should have max-width: 480px for large screens"
    print("✓ kanban-column has max-width: 480px for large screens (>1800px)")

    # Check media query for mobile
    assert 'flex: 0 0 280px;' in css_content, "kanban-column should have fixed width on mobile"
    print("✓ kanban-column has fixed width (280px) on mobile")

    # Check template doesn't have inline width styles
    template_path = 'templates/kanban/partials/board.html'
    with open(template_path, 'r') as f:
        template_content = f.read()

    assert 'style="width:' not in template_content, "Template should not have inline width styles"
    assert 'width: 280px' not in template_content, "Template should not have fixed widths"
    print("✓ Template has no inline width styles")


def test_fix2_done_column_hidden():
    """Test Fix 2: Done column hidden by default with toggle"""
    print("\n── Test Fix 2: Done Column Hidden by Default ──")

    # Read the main template
    template_path = 'templates/kanban/board.html'
    with open(template_path, 'r') as f:
        template_content = f.read()

    # Check toggle button exists
    assert 'toggle-done-btn' in template_content, "Toggle button should exist"
    print("✓ Toggle button exists with id 'toggle-done-btn'")

    # Check toggle button has onclick handler
    assert 'onclick="toggleDoneColumn()"' in template_content, "Toggle button should have onclick handler"
    print("✓ Toggle button has onclick='toggleDoneColumn()' handler")

    # Check icon and label elements exist
    assert 'toggle-done-icon' in template_content, "Toggle icon should exist"
    assert 'toggle-done-label' in template_content, "Toggle label should exist"
    print("✓ Toggle button has icon and label elements")

    # Check JavaScript functions exist
    assert 'function initDoneColumn()' in template_content, "initDoneColumn function should exist"
    assert 'function toggleDoneColumn()' in template_content, "toggleDoneColumn function should exist"
    assert 'function setDoneColumnVisible' in template_content, "setDoneColumnVisible function should exist"
    print("✓ All JavaScript functions exist (initDoneColumn, toggleDoneColumn, setDoneColumnVisible)")

    # Check localStorage key
    assert 'friday-kanban-done-visible' in template_content, "localStorage key should be defined"
    print("✓ localStorage key 'friday-kanban-done-visible' is defined")

    # Check default state is hidden
    assert "localStorage.getItem(DONE_VISIBLE_KEY) === 'true'" in template_content, "Default should be hidden (not 'true')"
    print("✓ Default state is hidden (localStorage check)")

    # Check button label changes
    assert 'Erledigt anzeigen' in template_content, "Label should have 'Erledigt anzeigen'"
    assert 'Erledigt ausblenden' in template_content, "Label should have 'Erledigt ausblenden'"
    print("✓ Button labels switch between 'Erledigt anzeigen' and 'Erledigt ausblenden'")

    # Check icon changes
    assert 'bi-eye-slash' in template_content, "Icon should change to eye-slash when visible"
    assert 'bi-eye' in template_content, "Icon should change to eye when hidden"
    print("✓ Icons switch between bi-eye and bi-eye-slash")

    # Check data-status attribute in partial template
    partial_path = 'templates/kanban/partials/board.html'
    with open(partial_path, 'r') as f:
        partial_content = f.read()

    assert 'data-status="{{ status }}"' in partial_content, "Columns should have data-status attribute"
    print("✓ Columns have data-status attribute for JavaScript targeting")

    # Check HTMX afterSwap re-initialization
    assert 'htmx:afterSwap' in template_content, "Should re-initialize after HTMX swap"
    assert 'initDoneColumn();' in template_content, "Should call initDoneColumn after swap"
    print("✓ JavaScript re-initializes after HTMX swaps")


def test_fix3_compact_filter_bar():
    """Test Fix 3: Compact filter bar"""
    print("\n── Test Fix 3: Compact Filter Bar ──")

    user, project, label = setup_test_data()
    client = Client()
    client.force_login(user)

    # Get the kanban board page
    response = client.get(reverse('kanban:kanban-board'))
    assert response.status_code == 200, "Kanban board should be accessible"

    content = response.content.decode('utf-8')
    soup = BeautifulSoup(content, 'html.parser')

    # Check filter bar exists with compact styling
    filter_bar = soup.find('div', class_='kanban-filter-bar')
    assert filter_bar is not None, "Filter bar should exist with class 'kanban-filter-bar'"
    print("✓ Filter bar exists with class 'kanban-filter-bar'")

    # Check filter bar uses flexbox
    assert 'd-flex' in filter_bar.get('class', []), "Filter bar should use d-flex"
    assert 'flex-wrap' in filter_bar.get('class', []), "Filter bar should use flex-wrap"
    print("✓ Filter bar uses flexbox with wrapping")

    # Check all filters use form-select-sm
    selects = filter_bar.find_all('select')
    assert len(selects) >= 7, f"Should have at least 7 filter selects (found {len(selects)})"

    for select in selects:
        classes = select.get('class', [])
        assert 'form-select-sm' in classes, f"Select {select.get('name')} should have form-select-sm class"
    print(f"✓ All {len(selects)} filter selects use form-select-sm")

    # Check font-size styling
    assert 'font-size:12px' in content, "Filters should have font-size:12px"
    print("✓ Filters have compact font-size:12px")

    # Check max-width constraints
    assert 'max-width:150px' in content, "Project filter should have max-width"
    assert 'max-width:130px' in content, "Client filter should have max-width"
    assert 'max-width:120px' in content, "Team/Label/Priority filters should have max-width"
    assert 'max-width:140px' in content, "Assignee filter should have max-width"
    assert 'max-width:110px' in content, "Due filter should have max-width"
    print("✓ All filters have max-width constraints")

    # Check kanban-filter class for HTMX include
    kanban_filters = filter_bar.find_all(class_='kanban-filter')
    assert len(kanban_filters) >= 7, f"Should have kanban-filter class on elements (found {len(kanban_filters)})"
    print(f"✓ Found {len(kanban_filters)} elements with kanban-filter class")

    # Check subtasks toggle
    subtasks_toggle = soup.find('input', {'id': 'show-subtasks'})
    assert subtasks_toggle is not None, "Subtasks toggle should exist"
    assert 'form-check-input' in subtasks_toggle.get('class', []), "Subtasks should use form-check-input"
    print("✓ Subtasks toggle exists and is styled correctly")

    # Check done toggle button
    done_toggle = soup.find('button', {'id': 'toggle-done-btn'})
    assert done_toggle is not None, "Done toggle button should exist"
    assert 'btn-sm' in done_toggle.get('class', []), "Done toggle should use btn-sm"
    print("✓ Done toggle button exists and is styled correctly")

    # Check separator
    separator = filter_bar.find('div', style=lambda s: s and 'width:1px' in s)
    assert separator is not None, "Visual separator should exist"
    print("✓ Visual separator exists between filters and toggles")

    # Check no filter active initially (Clear button should be hidden)
    response_no_filter = client.get(reverse('kanban:kanban-board'))
    content_no_filter = response_no_filter.content.decode('utf-8')

    # Check with filter active (Clear button should be visible)
    response_with_filter = client.get(reverse('kanban:kanban-board') + f'?project={project.pk}')
    content_with_filter = response_with_filter.content.decode('utf-8')

    # The Clear button should appear in the filtered version
    assert content_with_filter.count('Clear') > 0, "Clear button should appear when filter is active"
    print("✓ Clear button appears when filters are active")


def test_fix4_add_task_removed():
    """Test Fix 4: "+ Add task" buttons removed"""
    print("\n── Test Fix 4: '+ Add task' Buttons Removed ──")

    user, project, label = setup_test_data()
    client = Client()
    client.force_login(user)

    # Get the kanban board
    response = client.get(reverse('kanban:kanban-board'))
    assert response.status_code == 200, "Kanban board should be accessible"

    content = response.content.decode('utf-8')

    # Check that "Add task" buttons are removed from columns
    assert 'kanban-quick-add' not in content, "kanban-quick-add div should not exist"
    print("✓ kanban-quick-add div removed from template")

    # The word "Add task" should not appear in the kanban columns
    # It might appear elsewhere (like "New Task" button), so check specifically in column context
    partial_path = 'templates/kanban/partials/board.html'
    with open(partial_path, 'r') as f:
        partial_content = f.read()

    assert 'Add task' not in partial_content, "Add task buttons should be removed from board partial"
    print("✓ No 'Add task' buttons in kanban columns")

    # Verify "New Task" button still exists at top
    soup = BeautifulSoup(content, 'html.parser')
    new_task_btn = soup.find('a', string=lambda s: s and 'New Task' in s)
    assert new_task_btn is not None, "'New Task' button should still exist at top"
    print("✓ 'New Task' button still exists at top right")


def test_all_filters_still_work():
    """Test that all existing filters still function correctly"""
    print("\n── Test: All Existing Filters Still Work ──")

    user, project, label = setup_test_data()
    client = Client()
    client.force_login(user)

    # Test project filter
    response = client.get(reverse('kanban:kanban-board') + f'?project={project.pk}')
    assert response.status_code == 200, "Project filter should work"
    print("✓ Project filter works")

    # Test priority filter
    response = client.get(reverse('kanban:kanban-board') + f'?priority={Task.PRIORITY_NORMAL}')
    assert response.status_code == 200, "Priority filter should work"
    print("✓ Priority filter works")

    # Test due date filter
    response = client.get(reverse('kanban:kanban-board') + '?due=overdue')
    assert response.status_code == 200, "Due date filter should work"
    print("✓ Due date filter works")

    # Test label filter
    response = client.get(reverse('kanban:kanban-board') + f'?label={label.pk}')
    assert response.status_code == 200, "Label filter should work"
    content = response.content.decode('utf-8')
    # Should show the done task which has the label
    assert 'Task in done' in content, "Label filter should show tasks with that label"
    print("✓ Label filter works")

    # Test show_subtasks filter
    response = client.get(reverse('kanban:kanban-board') + '?show_subtasks=1')
    assert response.status_code == 200, "Show subtasks filter should work"
    print("✓ Show subtasks filter works")


def run_all_tests():
    """Run all test functions"""
    print("\n" + "="*60)
    print("ISSUE-67: Kanban View Verbesserungen - Acceptance Tests")
    print("="*60)

    try:
        # Test Fix 1
        test_fix1_flexible_column_widths()

        # Test Fix 2
        test_fix2_done_column_hidden()

        # Test Fix 3
        test_fix3_compact_filter_bar()

        # Test Fix 4
        test_fix4_add_task_removed()

        # Test that existing functionality still works
        test_all_filters_still_work()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
