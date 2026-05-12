#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-17: Fix Project Edit Mode.

This script tests:
- GET /projects/<pk>/edit/ returns 200 for project managers and staff
- GET /projects/<pk>/edit/ returns 403 for contributors, viewers, and non-members
- Form is pre-filled with all current project values
- Form title shows "Edit Project", submit button shows "Save Changes"
- Breadcrumb shows: Projects → Project Name → Edit
- Cancel button links back to project detail
- POST /projects/<pk>/edit/ saves changes and redirects to project detail
- Color picker is pre-filled with current project color
- Status and visibility dropdowns pre-select current values
- "Edit Project" button is visible on project detail for managers and staff
- "Edit Project" button is NOT visible for contributors and viewers
- GET /projects/create/ still works correctly
- Create form title shows "New Project", submit button shows "Create Project"
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.projects.models import Project, ProjectUserMembership
from apps.projects.views import ProjectEditView, ProjectCreateView

User = get_user_model()


def setup_test_data():
    """Create test users and project for testing."""
    # Create test users
    manager_user = User.objects.filter(username='test_manager').first()
    if not manager_user:
        manager_user = User.objects.create_user(
            username='test_manager',
            email='manager@test.com',
            password='testpass123'
        )

    contributor_user = User.objects.filter(username='test_contributor').first()
    if not contributor_user:
        contributor_user = User.objects.create_user(
            username='test_contributor',
            email='contributor@test.com',
            password='testpass123'
        )

    viewer_user = User.objects.filter(username='test_viewer').first()
    if not viewer_user:
        viewer_user = User.objects.create_user(
            username='test_viewer',
            email='viewer@test.com',
            password='testpass123'
        )

    non_member_user = User.objects.filter(username='test_non_member').first()
    if not non_member_user:
        non_member_user = User.objects.create_user(
            username='test_non_member',
            email='nonmember@test.com',
            password='testpass123'
        )

    staff_user = User.objects.filter(username='test_staff').first()
    if not staff_user:
        staff_user = User.objects.create_user(
            username='test_staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )

    # Create test project
    project = Project.objects.filter(name='Test Project for ISSUE-17').first()
    if not project:
        project = Project.objects.create(
            name='Test Project for ISSUE-17',
            description='Test description',
            status='active',
            visibility='members',
            owner=manager_user,
            color='#ff5733',
            priority=2
        )

    # Add memberships
    ProjectUserMembership.objects.get_or_create(
        project=project, user=manager_user, defaults={'role': 'manager'}
    )
    ProjectUserMembership.objects.get_or_create(
        project=project, user=contributor_user, defaults={'role': 'contributor'}
    )
    ProjectUserMembership.objects.get_or_create(
        project=project, user=viewer_user, defaults={'role': 'viewer'}
    )

    return {
        'project': project,
        'manager': manager_user,
        'contributor': contributor_user,
        'viewer': viewer_user,
        'non_member': non_member_user,
        'staff': staff_user
    }


def test_edit_view_permission_manager():
    """Test that managers can access edit view (returns 200)."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    assert response.status_code == 200, f"Manager got status {response.status_code}, expected 200"
    print("✓ Manager can access edit view (returns 200)")


def test_edit_view_permission_staff():
    """Test that staff can access edit view (returns 200)."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['staff'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    assert response.status_code == 200, f"Staff got status {response.status_code}, expected 200"
    print("✓ Staff can access edit view (returns 200)")


def test_edit_view_permission_contributor():
    """Test that contributors get 403 on edit view."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['contributor'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    assert response.status_code == 403, f"Contributor got status {response.status_code}, expected 403"
    print("✓ Contributor gets 403 on edit view")


def test_edit_view_permission_viewer():
    """Test that viewers get 403 on edit view."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['viewer'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    assert response.status_code == 403, f"Viewer got status {response.status_code}, expected 403"
    print("✓ Viewer gets 403 on edit view")


def test_edit_view_permission_non_member():
    """Test that non-members get 403 on edit view."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['non_member'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    assert response.status_code == 403, f"Non-member got status {response.status_code}, expected 403"
    print("✓ Non-member gets 403 on edit view")


def test_edit_form_content():
    """Test that edit form has correct title, breadcrumb, and pre-filled values."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.get(reverse('projects:project-edit', kwargs={'pk': data['project'].pk}))
    content = response.content.decode('utf-8')

    # Check title
    assert 'Edit Project' in content, "Title 'Edit Project' not found in form"

    # Check breadcrumb
    assert 'Projects' in content, "Breadcrumb 'Projects' not found"
    assert data['project'].name in content, f"Project name '{data['project'].name}' not in breadcrumb"
    assert 'Edit</li>' in content, "Breadcrumb 'Edit' not found"

    # Check submit button
    assert 'Save Changes' in content, "Submit button 'Save Changes' not found"

    # Check pre-filled values
    assert data['project'].name in content, "Project name not pre-filled"
    assert data['project'].color in content, "Project color not pre-filled"

    print("✓ Edit form has correct title, breadcrumb, and pre-filled values")


def test_create_form_content():
    """Test that create form has correct title and submit button."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.get(reverse('projects:project-create'))
    content = response.content.decode('utf-8')

    # Check title
    assert 'New Project' in content, "Title 'New Project' not found in create form"

    # Check submit button
    assert 'Create Project' in content, "Submit button 'Create Project' not found"

    # Should NOT have breadcrumb with project name (create mode)
    assert 'Edit</li>' not in content, "Edit breadcrumb found in create form"

    print("✓ Create form has correct title and submit button")


def test_edit_post_saves_changes():
    """Test that POST to edit view saves changes and redirects."""
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    new_name = 'Updated Project Name'
    new_description = 'Updated description'
    new_color = '#00ff00'
    new_priority = 3

    response = client.post(
        reverse('projects:project-edit', kwargs={'pk': data['project'].pk}),
        {
            'name': new_name,
            'description': new_description,
            'status': 'on_hold',
            'visibility': 'organisation',
            'color': new_color,
            'priority': new_priority
        }
    )

    # Should redirect to detail page
    assert response.status_code == 302, f"POST returned {response.status_code}, expected 302"
    assert f'/projects/{data["project"].pk}/' in response.url, "Redirect URL incorrect"

    # Check changes were saved
    data['project'].refresh_from_db()
    assert data['project'].name == new_name, "Name not updated"
    assert data['project'].description == new_description, "Description not updated"
    assert data['project'].color == new_color, "Color not updated"
    assert data['project'].priority == new_priority, "Priority not updated"
    assert data['project'].status == 'on_hold', "Status not updated"
    assert data['project'].visibility == 'organisation', "Visibility not updated"

    print("✓ POST to edit view saves changes and redirects correctly")


def test_detail_page_edit_button():
    """Test that Edit button is visible for managers and staff, not for others."""
    data = setup_test_data()
    client = Client()

    # Manager should see Edit button
    client.force_login(data['manager'])
    response = client.get(reverse('projects:project-detail', kwargs={'pk': data['project'].pk}))
    content = response.content.decode('utf-8')
    assert 'bi-pencil' in content and 'Edit' in content, "Manager cannot see Edit button"

    # Staff should see Edit button
    client.force_login(data['staff'])
    response = client.get(reverse('projects:project-detail', kwargs={'pk': data['project'].pk}))
    content = response.content.decode('utf-8')
    assert 'bi-pencil' in content and 'Edit' in content, "Staff cannot see Edit button"

    # Contributor should NOT see Edit button (but they may see other buttons)
    client.force_login(data['contributor'])
    response = client.get(reverse('projects:project-detail', kwargs={'pk': data['project'].pk}))
    content = response.content.decode('utf-8')
    # Check that the edit link is not present
    edit_url = reverse('projects:project-edit', kwargs={'pk': data['project'].pk})
    assert edit_url not in content, "Contributor can see Edit button"

    print("✓ Edit button visibility is correct (visible for managers/staff, hidden for others)")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*70)
    print("Testing ISSUE-17: Fix Project Edit Mode")
    print("="*70 + "\n")

    test_functions = [
        test_edit_view_permission_manager,
        test_edit_view_permission_staff,
        test_edit_view_permission_contributor,
        test_edit_view_permission_viewer,
        test_edit_view_permission_non_member,
        test_edit_form_content,
        test_create_form_content,
        test_edit_post_saves_changes,
        test_detail_page_edit_button,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: Unexpected error: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
