#!/usr/bin/env python
"""
Simplified acceptance tests for ISSUE-51: Erweiterung Status-Felder (Projekte + Tasks)

This script tests code-level changes without requiring a database:
1. Project model: new status choices (production, end_of_life, deferred)
2. Task model: new status choice (waiting)
3. Status color filter: returns correct colors for new statuses
4. Template files: include new tabs and columns
5. CSS file: includes waiting status styling
"""

import os
import sys


def test_project_status_choices():
    """Test 1: Project model has new status choices."""
    print("\n" + "=" * 70)
    print("TEST 1: Project Status Choices")
    print("=" * 70)

    # Import Django models
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    import django
    django.setup()
    from apps.projects.models import Project

    # Check that all new status constants exist
    assert hasattr(Project, 'STATUS_PRODUCTION'), "STATUS_PRODUCTION constant missing"
    assert hasattr(Project, 'STATUS_END_OF_LIFE'), "STATUS_END_OF_LIFE constant missing"
    assert hasattr(Project, 'STATUS_DEFERRED'), "STATUS_DEFERRED constant missing"

    # Check values
    assert Project.STATUS_PRODUCTION == 'production', "STATUS_PRODUCTION value incorrect"
    assert Project.STATUS_END_OF_LIFE == 'end_of_life', "STATUS_END_OF_LIFE value incorrect"
    assert Project.STATUS_DEFERRED == 'deferred', "STATUS_DEFERRED value incorrect"

    # Check STATUS_CHOICES contains all new statuses
    status_values = [s[0] for s in Project.STATUS_CHOICES]
    assert 'production' in status_values, "production not in STATUS_CHOICES"
    assert 'end_of_life' in status_values, "end_of_life not in STATUS_CHOICES"
    assert 'deferred' in status_values, "deferred not in STATUS_CHOICES"

    # Check display labels
    status_dict = dict(Project.STATUS_CHOICES)
    assert status_dict['production'] == 'Production', "production label incorrect"
    assert status_dict['end_of_life'] == 'End of Life', "end_of_life label incorrect"
    assert status_dict['deferred'] == 'Zurückgestellt', "deferred label incorrect"

    print("✓ All project status constants exist")
    print("✓ STATUS_CHOICES includes production, end_of_life, deferred")
    print("✓ Display labels are correct")
    print(f"  - production: {status_dict['production']}")
    print(f"  - end_of_life: {status_dict['end_of_life']}")
    print(f"  - deferred: {status_dict['deferred']}")


def test_task_status_choices():
    """Test 2: Task model has new status choice."""
    print("\n" + "=" * 70)
    print("TEST 2: Task Status Choices")
    print("=" * 70)

    from apps.tasks.models import Task

    # Check that waiting status constant exists
    assert hasattr(Task, 'STATUS_WAITING'), "STATUS_WAITING constant missing"
    assert Task.STATUS_WAITING == 'waiting', "STATUS_WAITING value incorrect"

    # Check STATUS_CHOICES contains waiting
    status_values = [s[0] for s in Task.STATUS_CHOICES]
    assert 'waiting' in status_values, "waiting not in STATUS_CHOICES"

    # Check display label
    status_dict = dict(Task.STATUS_CHOICES)
    assert status_dict['waiting'] == 'Waiting', "waiting label incorrect"

    # Check waiting is positioned between in_progress and review
    status_order = [s[0] for s in Task.STATUS_CHOICES]
    in_progress_idx = status_order.index('in_progress')
    waiting_idx = status_order.index('waiting')
    review_idx = status_order.index('review')

    assert in_progress_idx < waiting_idx < review_idx, \
        "waiting should be between in_progress and review"

    print("✓ Task STATUS_WAITING constant exists")
    print("✓ STATUS_CHOICES includes waiting")
    print(f"✓ waiting positioned correctly: {status_order}")
    print(f"  - Position: {waiting_idx} (between {in_progress_idx} and {review_idx})")


def test_status_color_filter():
    """Test 3: status_color filter returns correct colors."""
    print("\n" + "=" * 70)
    print("TEST 3: Status Color Filter")
    print("=" * 70)

    from apps.core.templatetags.friday_tags import status_color
    from apps.projects.models import Project

    # Create mock project objects
    class MockProject:
        def __init__(self, status):
            self.status = status

    # Test production - should be dark blue
    proj_prod = MockProject('production')
    color = status_color(proj_prod)
    assert color == '#1e3a5f', f"production color should be #1e3a5f, got {color}"

    # Test deferred - should be purple
    proj_def = MockProject('deferred')
    color = status_color(proj_def)
    assert color == '#6b21a8', f"deferred color should be #6b21a8, got {color}"

    # Test end_of_life - should be gray
    proj_eol = MockProject('end_of_life')
    color = status_color(proj_eol)
    assert color == '#374151', f"end_of_life color should be #374151, got {color}"

    print("✓ production status returns dark blue (#1e3a5f)")
    print("✓ deferred status returns purple (#6b21a8)")
    print("✓ end_of_life status returns gray (#374151)")


def test_project_list_template():
    """Test 4: Project list template includes new tabs."""
    print("\n" + "=" * 70)
    print("TEST 4: Project List Template")
    print("=" * 70)

    template_path = '/home/runner/work/Friday/Friday/templates/projects/list.html'
    with open(template_path, 'r') as f:
        content = f.read()

    # Check that new tabs exist
    assert 'href="?status=production"' in content, "Production tab missing"
    assert 'href="?status=deferred"' in content, "Zurückgestellt tab missing"

    # Check that tab labels are in German
    assert '>Production<' in content, "Production tab label missing"
    assert '>Zurückgestellt<' in content, "Zurückgestellt tab label missing"

    # Count total tabs (should be 7: Alle, Aktiv, Planung, Production, Pausiert, Zurückgestellt, Abgeschlossen)
    tab_count = content.count('<li class="nav-item">')
    assert tab_count == 7, f"Expected 7 tabs, found {tab_count}"

    print("✓ Production tab exists in project list")
    print("✓ Zurückgestellt tab exists in project list")
    print("✓ Tab labels are in German")
    print(f"✓ Total tabs: {tab_count}")


def test_status_badge_template():
    """Test 5: Status badge template includes new statuses."""
    print("\n" + "=" * 70)
    print("TEST 5: Status Badge Template")
    print("=" * 70)

    template_path = '/home/runner/work/Friday/Friday/templates/projects/partials/status_badge.html'
    with open(template_path, 'r') as f:
        content = f.read()

    # Check that new status conditions exist
    assert "project.status == 'production'" in content, "production status check missing"
    assert "project.status == 'deferred'" in content, "deferred status check missing"
    assert "project.status == 'end_of_life'" in content, "end_of_life status check missing"

    # Check for purple color for deferred
    assert '#6b21a8' in content, "deferred purple color missing"

    print("✓ production status condition exists")
    print("✓ deferred status condition exists")
    print("✓ end_of_life status condition exists")
    print("✓ deferred uses purple color (#6b21a8)")


def test_kanban_board_columns():
    """Test 6: Kanban board automatically includes waiting column."""
    print("\n" + "=" * 70)
    print("TEST 6: Kanban Board Columns")
    print("=" * 70)

    # The kanban board template loops through STATUS_CHOICES,
    # so it will automatically include the waiting column
    from apps.tasks.models import Task

    status_values = [s[0] for s in Task.STATUS_CHOICES]
    status_labels = dict(Task.STATUS_CHOICES)

    assert 'waiting' in status_values, "waiting not in STATUS_CHOICES"
    assert status_labels['waiting'] == 'Waiting', "waiting label incorrect"

    # Verify the kanban view uses STATUS_CHOICES
    view_path = '/home/runner/work/Friday/Friday/apps/kanban/views.py'
    with open(view_path, 'r') as f:
        view_content = f.read()

    assert 'Task.STATUS_CHOICES' in view_content, \
        "Kanban view should use Task.STATUS_CHOICES"

    # Verify the kanban template loops through status_choices
    template_path = '/home/runner/work/Friday/Friday/templates/kanban/partials/board.html'
    with open(template_path, 'r') as f:
        template_content = f.read()

    assert 'for status, label in status_choices' in template_content, \
        "Kanban template should loop through status_choices"

    print("✓ Kanban board will automatically include waiting column")
    print("✓ Kanban view uses Task.STATUS_CHOICES")
    print("✓ Kanban template loops through status_choices")
    print(f"✓ Total columns: {len(status_values)}")


def test_css_styling():
    """Test 7: CSS file includes waiting status styling."""
    print("\n" + "=" * 70)
    print("TEST 7: CSS Styling for Waiting Status")
    print("=" * 70)

    css_path = '/home/runner/work/Friday/Friday/static/css/friday.css'
    with open(css_path, 'r') as f:
        css_content = f.read()

    # Check for waiting status styling
    assert '[data-status="waiting"]' in css_content, \
        "CSS should include waiting status selector"

    # Check for amber/orange color (#f59e0b)
    assert '#f59e0b' in css_content, \
        "CSS should include amber/orange color for waiting status"

    # Check for border-left styling
    assert 'border-left' in css_content and 'waiting' in css_content, \
        "CSS should include border-left styling for waiting tasks"

    # Check for opacity styling
    assert 'opacity: 0.85' in css_content, \
        "CSS should include opacity for waiting tasks"

    print("✓ CSS includes [data-status=\"waiting\"] selector")
    print("✓ CSS includes amber/orange color (#f59e0b)")
    print("✓ CSS includes border-left styling for waiting tasks")
    print("✓ CSS includes opacity: 0.85 for visual distinction")


def test_acceptance_criteria():
    """Test 8: Verify all acceptance criteria are met."""
    print("\n" + "=" * 70)
    print("TEST 8: Acceptance Criteria Verification")
    print("=" * 70)

    from apps.projects.models import Project
    from apps.tasks.models import Task
    from apps.core.templatetags.friday_tags import status_color

    # Project Status Criteria
    criteria = [
        ('production in STATUS_CHOICES',
         'production' in [s[0] for s in Project.STATUS_CHOICES]),
        ('end_of_life in STATUS_CHOICES',
         'end_of_life' in [s[0] for s in Project.STATUS_CHOICES]),
        ('deferred in STATUS_CHOICES',
         'deferred' in [s[0] for s in Project.STATUS_CHOICES]),
        ('production color is dark blue',
         status_color(type('P', (), {'status': 'production'})()) == '#1e3a5f'),
        ('deferred color is purple',
         status_color(type('P', (), {'status': 'deferred'})()) == '#6b21a8'),
        ('end_of_life color is gray',
         status_color(type('P', (), {'status': 'end_of_life'})()) == '#374151'),
    ]

    # Task Status Criteria
    criteria += [
        ('waiting in STATUS_CHOICES',
         'waiting' in [s[0] for s in Task.STATUS_CHOICES]),
        ('waiting positioned correctly',
         True),  # Already verified in test 2
    ]

    # Template Criteria
    template_path = '/home/runner/work/Friday/Friday/templates/projects/list.html'
    with open(template_path, 'r') as f:
        list_content = f.read()

    criteria += [
        ('Production tab exists', 'href="?status=production"' in list_content),
        ('Zurückgestellt tab exists', 'href="?status=deferred"' in list_content),
    ]

    # CSS Criteria
    css_path = '/home/runner/work/Friday/Friday/static/css/friday.css'
    with open(css_path, 'r') as f:
        css_content = f.read()

    criteria += [
        ('Waiting CSS styling exists', '[data-status="waiting"]' in css_content),
        ('Waiting color is amber', '#f59e0b' in css_content),
    ]

    # Print results
    passed = 0
    failed = 0
    for desc, result in criteria:
        if result:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc}")
            failed += 1

    print(f"\nCriteria passed: {passed}/{len(criteria)}")

    if failed > 0:
        raise AssertionError(f"{failed} acceptance criteria failed")


def run_all_tests():
    """Run all acceptance tests."""
    print("\n" + "=" * 70)
    print("ISSUE-51: Status Fields Expansion - Acceptance Tests")
    print("=" * 70)

    try:
        test_project_status_choices()
        test_task_status_choices()
        test_status_color_filter()
        test_project_list_template()
        test_status_badge_template()
        test_kanban_board_columns()
        test_css_styling()
        test_acceptance_criteria()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        print("\nSummary:")
        print("  - Project model: 3 new status choices added")
        print("  - Task model: 1 new status choice added")
        print("  - Template tags: status_color filter updated")
        print("  - Project list: 2 new tabs added (Production, Zurückgestellt)")
        print("  - Kanban board: waiting column automatically included")
        print("  - CSS: waiting status styling added")
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
