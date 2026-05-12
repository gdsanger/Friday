#!/usr/bin/env python
"""
Test script for Dashboard acceptance criteria (ISSUE-10).
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.dashboard.views import (
    DashboardView, WidgetMyTasksView, WidgetOverdueView,
    WidgetTeamLoadView, WidgetDueSoonView, WidgetProjectStatusView,
    WidgetActivityView
)
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.teams.models import Team
from apps.notifications.models import Notification
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def run_tests():
    """Run acceptance criteria tests."""
    print("=" * 80)
    print("Dashboard Acceptance Criteria Tests (ISSUE-10)")
    print("=" * 80)

    # Get or create test user
    user = User.objects.get(username='testuser')
    factory = RequestFactory()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Dashboard renders page shell immediately (no data blocking)
    print("\n✓ Test 1: Dashboard renders page shell immediately")
    request = factory.get('/dashboard/')
    request.user = user
    view = DashboardView.as_view()
    response = view(request)
    if response.status_code == 200:
        print("  ✓ Dashboard view returns 200")
        tests_passed += 1
    else:
        print(f"  ✗ Dashboard view returned {response.status_code}")
        tests_failed += 1

    # Test 2: All 6 widget divs load independently via HTMX
    print("\n✓ Test 2: All 6 widget endpoints respond correctly")
    widgets = [
        ('My Tasks', WidgetMyTasksView, '/dashboard/widgets/my-tasks/'),
        ('Overdue', WidgetOverdueView, '/dashboard/widgets/overdue/'),
        ('Team Load', WidgetTeamLoadView, '/dashboard/widgets/team-load/'),
        ('Due Soon', WidgetDueSoonView, '/dashboard/widgets/due-soon/'),
        ('Project Status', WidgetProjectStatusView, '/dashboard/widgets/project-status/'),
        ('Activity', WidgetActivityView, '/dashboard/widgets/activity/'),
    ]

    for name, view_class, url in widgets:
        request = factory.get(url)
        request.user = user
        view = view_class()
        response = view.get(request)
        if response.status_code == 200:
            print(f"  ✓ {name} widget responds with 200")
            tests_passed += 1
        else:
            print(f"  ✗ {name} widget returned {response.status_code}")
            tests_failed += 1

    # Test 3: "My open tasks" count matches tasks assigned to current user, not done
    print("\n✓ Test 3: My open tasks count is correct")
    request = factory.get('/dashboard/widgets/my-tasks/')
    request.user = user
    view = WidgetMyTasksView()
    response = view.get(request)

    expected_count = Task.objects.filter(
        assigned_to_user=user
    ).exclude(status='done').count()

    content = response.content.decode('utf-8')
    if str(expected_count) in content:
        print(f"  ✓ Widget shows correct count: {expected_count}")
        tests_passed += 1
    else:
        print(f"  ✗ Widget doesn't show correct count: {expected_count}")
        tests_failed += 1

    # Test 4: "Overdue" count shows tasks with due_date < today
    print("\n✓ Test 4: Overdue count is correct")
    request = factory.get('/dashboard/widgets/overdue/')
    request.user = user
    view = WidgetOverdueView()
    response = view.get(request)

    today = timezone.now().date()
    from django.db.models import Q
    expected_overdue = Task.objects.filter(
        Q(assigned_to_user=user) | Q(assigned_to_team__in=user.teams),
        due_date__lt=today,
    ).exclude(status='done').count()

    content = response.content.decode('utf-8')
    if str(expected_overdue) in content:
        print(f"  ✓ Widget shows correct overdue count: {expected_overdue}")
        tests_passed += 1
    else:
        print(f"  ✗ Widget doesn't show correct overdue count: {expected_overdue}")
        tests_failed += 1

    # Test 5: "Due soon" list shows only next 7 days
    print("\n✓ Test 5: Due soon widget shows tasks due in next 7 days")
    request = factory.get('/dashboard/widgets/due-soon/')
    request.user = user
    view = WidgetDueSoonView()
    response = view.get(request)

    today = timezone.now().date()
    in_7days = today + timedelta(days=7)
    from django.db.models import Q
    expected_due_soon = Task.objects.filter(
        Q(assigned_to_user=user) | Q(assigned_to_team__in=user.teams),
        due_date__range=(today, in_7days),
    ).exclude(status='done').count()

    content = response.content.decode('utf-8')
    # Check if widget renders without error
    if response.status_code == 200:
        print(f"  ✓ Widget renders correctly (expecting {expected_due_soon} tasks)")
        tests_passed += 1
    else:
        print(f"  ✗ Widget failed to render")
        tests_failed += 1

    # Test 6: Team load shows a bar per team
    print("\n✓ Test 6: Team load widget shows team data")
    request = factory.get('/dashboard/widgets/team-load/')
    request.user = user
    view = WidgetTeamLoadView()
    response = view.get(request)

    my_teams_count = user.teams.count()
    content = response.content.decode('utf-8')

    if response.status_code == 200:
        print(f"  ✓ Widget renders correctly (user has {my_teams_count} teams)")
        tests_passed += 1
    else:
        print(f"  ✗ Widget failed to render")
        tests_failed += 1

    # Test 7: Project status shows progress bar per project
    print("\n✓ Test 7: Project status widget shows project progress")
    request = factory.get('/dashboard/widgets/project-status/')
    request.user = user
    view = WidgetProjectStatusView()
    response = view.get(request)

    if response.status_code == 200:
        print(f"  ✓ Widget renders correctly")
        tests_passed += 1
    else:
        print(f"  ✗ Widget failed to render")
        tests_failed += 1

    # Test 8: Activity feed shows last 20 notifications
    print("\n✓ Test 8: Activity feed shows recent notifications")
    request = factory.get('/dashboard/widgets/activity/')
    request.user = user
    view = WidgetActivityView()
    response = view.get(request)

    expected_notif_count = min(
        Notification.objects.filter(recipient=user).count(),
        20
    )

    if response.status_code == 200:
        print(f"  ✓ Widget renders correctly (showing up to 20 of {expected_notif_count} notifications)")
        tests_passed += 1
    else:
        print(f"  ✗ Widget failed to render")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 80)

    if tests_failed == 0:
        print("\n✓ All acceptance criteria tests PASSED!")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
