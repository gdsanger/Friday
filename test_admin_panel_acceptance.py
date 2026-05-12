#!/usr/bin/env python
"""
Test script for Admin Panel implementation.
Tests access control, views, and key functionality.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from apps.admin_panel.views import (
    AdminDashboardView,
    AdminUserListView,
    AdminTeamListView,
    AdminAIMonitorView,
    AdminMailStatusView,
    AdminOrgSettingsView,
)

User = get_user_model()


def test_access_control():
    """Test that only staff users can access admin panel."""
    print("\n=== Testing Access Control ===")

    factory = RequestFactory()
    staff_user = User.objects.get(username='admin')
    regular_user = User.objects.get(username='testuser')

    # Test staff user can access
    request = factory.get('/admin-panel/')
    request.user = staff_user
    try:
        response = AdminDashboardView.as_view()(request)
        print(f"✓ Staff user can access dashboard (status: {response.status_code})")
    except PermissionDenied:
        print("✗ Staff user denied access to dashboard")
        return False

    # Test regular user is denied
    request = factory.get('/admin-panel/')
    request.user = regular_user
    try:
        response = AdminDashboardView.as_view()(request)
        print(f"✗ Regular user granted access to dashboard (status: {response.status_code})")
        return False
    except PermissionDenied:
        print("✓ Regular user correctly denied access to dashboard")

    return True


def test_dashboard_view():
    """Test dashboard view renders correctly."""
    print("\n=== Testing Dashboard View ===")

    factory = RequestFactory()
    staff_user = User.objects.get(username='admin')

    request = factory.get('/admin-panel/')
    request.user = staff_user

    response = AdminDashboardView.as_view()(request)

    if response.status_code == 200:
        print(f"✓ Dashboard view returns 200")

        # Check context data
        view = AdminDashboardView()
        view.setup(request)
        context = view.get_context_data()

        expected_keys = ['user_count', 'team_count', 'project_count', 'task_count', 'ai_tokens_today', 'ai_enabled']
        missing_keys = [key for key in expected_keys if key not in context]

        if not missing_keys:
            print(f"✓ Dashboard context contains all expected keys")
            print(f"  - Users: {context['user_count']}")
            print(f"  - Teams: {context['team_count']}")
            print(f"  - Projects: {context['project_count']}")
            print(f"  - Tasks: {context['task_count']}")
            return True
        else:
            print(f"✗ Dashboard context missing keys: {missing_keys}")
            return False
    else:
        print(f"✗ Dashboard view returns {response.status_code}")
        return False


def test_user_list_view():
    """Test user list view."""
    print("\n=== Testing User List View ===")

    factory = RequestFactory()
    staff_user = User.objects.get(username='admin')

    request = factory.get('/admin-panel/users/')
    request.user = staff_user

    response = AdminUserListView.as_view()(request)

    if response.status_code == 200:
        print(f"✓ User list view returns 200")

        # Check queryset
        view = AdminUserListView()
        view.setup(request)
        view.object_list = view.get_queryset()

        user_count = view.object_list.count()
        print(f"  - Found {user_count} users")

        if user_count >= 2:
            print(f"✓ User list contains expected users")
            return True
        else:
            print(f"✗ User list count incorrect")
            return False
    else:
        print(f"✗ User list view returns {response.status_code}")
        return False


def test_team_list_view():
    """Test team list view."""
    print("\n=== Testing Team List View ===")

    factory = RequestFactory()
    staff_user = User.objects.get(username='admin')

    request = factory.get('/admin-panel/teams/')
    request.user = staff_user

    response = AdminTeamListView.as_view()(request)

    if response.status_code == 200:
        print(f"✓ Team list view returns 200")
        return True
    else:
        print(f"✗ Team list view returns {response.status_code}")
        return False


def test_ai_monitor_view():
    """Test AI monitoring view."""
    print("\n=== Testing AI Monitor View ===")

    factory = RequestFactory()
    staff_user = User.objects.get(username='admin')

    request = factory.get('/admin-panel/ai/')
    request.user = staff_user

    response = AdminAIMonitorView.as_view()(request)

    if response.status_code == 200:
        print(f"✓ AI monitor view returns 200")
        return True
    else:
        print(f"✗ AI monitor view returns {response.status_code}")
        return False


def test_url_routing():
    """Test URL routing with Django test client."""
    print("\n=== Testing URL Routing ===")

    client = Client()

    # Login as staff user
    client.login(username='admin', password='admin123')

    urls_to_test = [
        ('/admin-panel/', 'Dashboard'),
        ('/admin-panel/users/', 'User List'),
        ('/admin-panel/teams/', 'Team List'),
        ('/admin-panel/ai/', 'AI Monitor'),
        ('/admin-panel/mail/', 'Mail Status'),
        ('/admin-panel/settings/', 'Organisation Settings'),
        ('/admin-panel/audit/', 'Audit Log'),
    ]

    all_passed = True
    for url, name in urls_to_test:
        response = client.get(url)
        if response.status_code == 200:
            print(f"✓ {name} accessible at {url}")
        else:
            print(f"✗ {name} returned {response.status_code} at {url}")
            all_passed = False

    # Test non-staff user is denied
    client.logout()
    client.login(username='testuser', password='test123')

    response = client.get('/admin-panel/')
    if response.status_code == 403:
        print(f"✓ Non-staff user correctly denied access (403)")
    else:
        print(f"✗ Non-staff user got status {response.status_code} instead of 403")
        all_passed = False

    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("ADMIN PANEL ACCEPTANCE TESTS")
    print("=" * 60)

    results = {
        'Access Control': test_access_control(),
        'Dashboard View': test_dashboard_view(),
        'User List View': test_user_list_view(),
        'Team List View': test_team_list_view(),
        'AI Monitor View': test_ai_monitor_view(),
        'URL Routing': test_url_routing(),
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
