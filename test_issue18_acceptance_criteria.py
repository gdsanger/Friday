#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-18.

This script tests:
- Team Detail view includes member management (add/remove)
- Team Detail view includes project assignment (assign/remove)
- HTMX interactions for member and project operations
- URL patterns for new views
- Permission checks for leads and staff
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from apps.teams.models import Team, TeamMembership
from apps.teams.views import TeamDetailView
from apps.projects.models import Project, ProjectTeamMembership

User = get_user_model()


def setup_test_data():
    """Create test users, teams, and projects."""
    # Clean up any existing test data first
    Team.objects.filter(slug__startswith='test-team-issue18').delete()
    Project.objects.filter(name__startswith='Test Project Issue18').delete()
    User.objects.filter(username__startswith='test_').filter(username__contains='issue18').delete()

    # Create staff user
    staff_user = User.objects.create_user(
        username='test_staff_issue18',
        email='staff18@test.com',
        password='testpass123',
        display_name='Test Staff Issue18',
        is_staff=True
    )

    # Create team lead user
    lead_user = User.objects.create_user(
        username='test_lead_issue18',
        email='lead18@test.com',
        password='testpass123',
        display_name='Test Lead Issue18'
    )

    # Create regular user
    regular_user = User.objects.create_user(
        username='test_regular_issue18',
        email='regular18@test.com',
        password='testpass123',
        display_name='Test Regular Issue18'
    )

    # Create another user to add
    add_user = User.objects.create_user(
        username='test_add_issue18',
        email='add18@test.com',
        password='testpass123',
        display_name='Test Add Issue18'
    )

    # Create test team
    team = Team.objects.create(
        name='Test Team Issue18',
        slug='test-team-issue18',
        description='Test team for issue 18',
        color='#6366f1',
        icon='people-fill'
    )

    # Add lead to team
    TeamMembership.objects.create(
        team=team,
        user=lead_user,
        role='lead'
    )

    # Add regular member to team
    TeamMembership.objects.create(
        team=team,
        user=regular_user,
        role='member'
    )

    # Create test projects
    project1 = Project.objects.create(
        name='Test Project Issue18 A',
        description='Test project A for issue 18',
        status='active',
        color='#2980b9',
        owner=staff_user
    )

    project2 = Project.objects.create(
        name='Test Project Issue18 B',
        description='Test project B for issue 18',
        status='planning',
        color='#16a085',
        owner=staff_user
    )

    # Assign team to project1 only
    ProjectTeamMembership.objects.create(
        project=project1,
        team=team,
        role='contributor'
    )

    return {
        'staff_user': staff_user,
        'lead_user': lead_user,
        'regular_user': regular_user,
        'add_user': add_user,
        'team': team,
        'project1': project1,
        'project2': project2,
    }


def test_team_detail_context():
    """Test that TeamDetailView includes all necessary context."""
    print("Testing TeamDetailView context...")
    data = setup_test_data()
    team = data['team']
    lead_user = data['lead_user']

    # Use RequestFactory to access context directly
    factory = RequestFactory()
    request = factory.get(reverse('teams:team-detail', kwargs={'slug': team.slug}))
    request.user = lead_user

    view = TeamDetailView()
    view.setup(request, slug=team.slug)
    view.object = view.get_object()
    context = view.get_context_data()

    assert 'memberships' in context, "memberships not in context"
    assert 'projects' in context, "projects not in context"
    assert 'available_projects' in context, "available_projects not in context"
    assert 'all_users' in context, "all_users not in context"
    assert 'is_lead' in context, "is_lead not in context"

    # Check that available_projects excludes projects team is already in
    available = list(context['available_projects'])
    assert data['project2'] in available, "project2 should be in available_projects"
    assert data['project1'] not in available, "project1 should NOT be in available_projects (already assigned)"

    print("✓ TeamDetailView context is correct")


def test_member_management_visibility():
    """Test that add member form is visible to leads and staff."""
    print("Testing member management form visibility...")
    data = setup_test_data()
    team = data['team']

    # Test as lead
    client = Client()
    client.force_login(data['lead_user'])
    url = reverse('teams:team-detail', kwargs={'slug': team.slug})
    response = client.get(url)
    content = response.content.decode()

    assert 'members/add/' in content, "Add member form URL not found for lead"
    assert 'Add Member' in content, "Add Member heading not found for lead"

    # Test as staff
    client.force_login(data['staff_user'])
    response = client.get(url)
    content = response.content.decode()

    assert 'members/add/' in content, "Add member form URL not found for staff"
    assert 'Add Member' in content, "Add Member heading not found for staff"

    # Test as regular member (should not see add form)
    client.force_login(data['regular_user'])
    response = client.get(url)
    content = response.content.decode()

    # Regular members should still see the member list but not the add form in the footer
    assert 'member-list' in content, "Member list not found"
    assert 'card-footer' not in content, "Add member form should not be visible to regular members"

    print("✓ Add member form visibility is correct")


def test_add_member_htmx():
    """Test adding a member via HTMX."""
    print("Testing add member via HTMX...")
    data = setup_test_data()
    team = data['team']
    add_user = data['add_user']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-member-add', kwargs={'slug': team.slug})
    response = client.post(url, {
        'user_id': add_user.pk,
        'role': 'guest'
    }, HTTP_HX_REQUEST='true')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify membership was created
    membership = TeamMembership.objects.filter(team=team, user=add_user).first()
    assert membership is not None, "Membership was not created"
    assert membership.role == 'guest', f"Expected role 'guest', got '{membership.role}'"

    print("✓ Add member via HTMX works")


def test_remove_member_htmx():
    """Test removing a member via HTMX."""
    print("Testing remove member via HTMX...")
    data = setup_test_data()
    team = data['team']
    regular_user = data['regular_user']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-member-remove', kwargs={
        'slug': team.slug,
        'user_id': regular_user.pk
    })
    response = client.post(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify membership was removed
    membership = TeamMembership.objects.filter(team=team, user=regular_user).first()
    assert membership is None, "Membership was not removed"

    print("✓ Remove member via HTMX works")


def test_project_assignment_urls():
    """Test that project assignment URLs exist."""
    print("Testing project assignment URLs...")
    data = setup_test_data()
    team = data['team']
    project = data['project2']

    # Test add URL
    add_url = reverse('teams:team-project-add', kwargs={'slug': team.slug})
    assert add_url == f'/teams/{team.slug}/projects/add/', f"Unexpected add URL: {add_url}"

    # Test remove URL
    remove_url = reverse('teams:team-project-remove', kwargs={
        'slug': team.slug,
        'project_pk': project.pk
    })
    assert remove_url == f'/teams/{team.slug}/projects/{project.pk}/remove/', f"Unexpected remove URL: {remove_url}"

    print("✓ Project assignment URLs are correct")


def test_assign_project_htmx():
    """Test assigning a project via HTMX."""
    print("Testing assign project via HTMX...")
    data = setup_test_data()
    team = data['team']
    project2 = data['project2']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-project-add', kwargs={'slug': team.slug})
    response = client.post(url, {
        'project_id': project2.pk,
        'role': 'viewer'
    }, HTTP_HX_REQUEST='true')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify membership was created
    membership = ProjectTeamMembership.objects.filter(project=project2, team=team).first()
    assert membership is not None, "Project team membership was not created"
    assert membership.role == 'viewer', f"Expected role 'viewer', got '{membership.role}'"

    print("✓ Assign project via HTMX works")


def test_remove_project_htmx():
    """Test removing a project via HTMX."""
    print("Testing remove project via HTMX...")
    data = setup_test_data()
    team = data['team']
    project1 = data['project1']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-project-remove', kwargs={
        'slug': team.slug,
        'project_pk': project1.pk
    })
    response = client.post(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify membership was removed
    membership = ProjectTeamMembership.objects.filter(project=project1, team=team).first()
    assert membership is None, "Project team membership was not removed"

    print("✓ Remove project via HTMX works")


def test_project_assignment_permissions():
    """Test that only leads and staff can assign/remove projects."""
    print("Testing project assignment permissions...")
    data = setup_test_data()
    team = data['team']
    project2 = data['project2']

    client = Client()
    client.force_login(data['regular_user'])

    # Try to assign project as regular member (should fail)
    url = reverse('teams:team-project-add', kwargs={'slug': team.slug})
    response = client.post(url, {
        'project_id': project2.pk,
        'role': 'contributor'
    })

    assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    print("✓ Project assignment permissions are correct")


def test_project_list_partial():
    """Test that project_list.html partial renders correctly."""
    print("Testing project_list.html partial...")
    data = setup_test_data()
    team = data['team']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-detail', kwargs={'slug': team.slug})
    response = client.get(url)
    content = response.content.decode()

    # Check for project list elements
    assert 'team-project-list' in content, "team-project-list not found"
    assert data['project1'].name in content, "Project1 name not found in content"

    # Check for assign form
    assert 'Assign to project' in content, "Assign form not found"

    # Check that available_projects are in the select
    assert data['project2'].name in content, "Available project not in select options"

    print("✓ project_list.html partial renders correctly")


def test_team_detail_layout():
    """Test that team detail page has the correct layout."""
    print("Testing team detail page layout...")
    data = setup_test_data()
    team = data['team']

    client = Client()
    client.force_login(data['lead_user'])

    url = reverse('teams:team-detail', kwargs={'slug': team.slug})
    response = client.get(url)
    content = response.content.decode()

    # Check for two-column layout
    assert 'col-lg-8' in content, "Left column (col-lg-8) not found"
    assert 'col-lg-4' in content, "Right column (col-lg-4) not found"

    # Check for member section
    assert 'Team Members' in content, "Team Members heading not found"
    assert 'member-list' in content, "member-list not found"

    # Check for project section
    assert 'Projects' in content, "Projects heading not found"

    # Check for team info section
    assert 'Team Info' in content, "Team Info heading not found"

    print("✓ Team detail page layout is correct")


def run_all_tests():
    """Run all acceptance criteria tests."""
    print("\n" + "="*60)
    print("ISSUE-18 Acceptance Criteria Tests")
    print("="*60 + "\n")

    tests = [
        test_team_detail_context,
        test_member_management_visibility,
        test_add_member_htmx,
        test_remove_member_htmx,
        test_project_assignment_urls,
        test_assign_project_htmx,
        test_remove_project_htmx,
        test_project_assignment_permissions,
        test_project_list_partial,
        test_team_detail_layout,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
