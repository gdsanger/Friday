#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-16.

This script tests:
- Team Creation view (staff only)
- User Assignment view (staff only)
- HTMX interactions for assigning/removing users from teams
- URL patterns for all new views
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse, resolve
from django.core.exceptions import PermissionDenied
from apps.teams.models import Team, TeamMembership

User = get_user_model()


def setup_test_data():
    """Create test users and teams."""
    # Create staff user
    staff_user = User.objects.filter(username='test_staff').first()
    if not staff_user:
        staff_user = User.objects.create_user(
            username='test_staff',
            email='staff@test.com',
            password='testpass123',
            display_name='Test Staff',
            is_staff=True
        )

    # Create regular user
    regular_user = User.objects.filter(username='test_regular').first()
    if not regular_user:
        regular_user = User.objects.create_user(
            username='test_regular',
            email='regular@test.com',
            password='testpass123',
            display_name='Test Regular'
        )

    # Create another regular user
    user2 = User.objects.filter(username='test_user2').first()
    if not user2:
        user2 = User.objects.create_user(
            username='test_user2',
            email='user2@test.com',
            password='testpass123',
            display_name='Test User 2'
        )

    # Create a test team
    test_team = Team.objects.filter(slug='test-team').first()
    if not test_team:
        test_team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            description='A test team',
            color='#6366f1',
            icon='people-fill'
        )

    return staff_user, regular_user, user2, test_team


def test_url_patterns():
    """Test that all new URL patterns are configured correctly."""
    print("\n" + "="*60)
    print("Testing URL Patterns")
    print("="*60)

    urls = [
        ('teams:team-create', [], 'TeamCreateView'),
        ('teams:team-user-list', [], 'TeamUserListView'),
        ('teams:team-user-assign', [1], 'TeamUserAssignView'),
        ('teams:team-user-remove', [1, 'test-team'], 'TeamUserRemoveView'),
    ]

    for url_name, args, expected_view in urls:
        try:
            url = reverse(url_name, args=args)
            resolver = resolve(url)
            view_name = resolver.func.__name__
            if expected_view in str(resolver.func):
                print(f"✓ {url_name:30} → {url:40} ({expected_view})")
            else:
                print(f"✗ {url_name:30} → URL resolves but view name mismatch")
        except Exception as e:
            print(f"✗ {url_name:30} → ERROR: {e}")


def test_team_create_view():
    """Test team creation functionality."""
    print("\n" + "="*60)
    print("Testing Team Creation")
    print("="*60)

    staff_user, regular_user, user2, test_team = setup_test_data()
    client = Client()

    # Test 1: GET request returns 403 for non-staff
    print("\n1. Testing non-staff user cannot access create page...")
    client.login(username='test_regular', password='testpass123')
    response = client.get(reverse('teams:team-create'))
    if response.status_code == 403:
        print("   ✓ Non-staff user correctly denied (403)")
    else:
        print(f"   ✗ Expected 403, got {response.status_code}")
    client.logout()

    # Test 2: GET request returns 200 for staff
    print("\n2. Testing staff user can access create page...")
    client.login(username='test_staff', password='testpass123')
    response = client.get(reverse('teams:team-create'))
    if response.status_code == 200:
        print("   ✓ Staff user can access create page (200)")
        if 'color_presets' in response.context:
            print("   ✓ Color presets provided in context")
        else:
            print("   ✗ Color presets missing from context")
    else:
        print(f"   ✗ Expected 200, got {response.status_code}")

    # Test 3: POST with empty name returns error
    print("\n3. Testing POST with empty name...")
    response = client.post(reverse('teams:team-create'), {
        'name': '',
        'description': 'Test description',
        'color': '#6366f1',
        'icon': 'star'
    })
    if response.status_code == 200 and 'error' in response.context:
        print("   ✓ Empty name validation works")
    else:
        print(f"   ✗ Validation failed (status: {response.status_code})")

    # Test 4: POST with valid data creates team
    print("\n4. Testing POST with valid data...")
    initial_count = Team.objects.count()
    response = client.post(reverse('teams:team-create'), {
        'name': 'New Test Team',
        'description': 'A newly created test team',
        'color': '#2980b9',
        'icon': 'rocket'
    })
    new_count = Team.objects.count()

    if new_count > initial_count:
        print("   ✓ Team created successfully")
        new_team = Team.objects.filter(name='New Test Team').first()
        if new_team:
            print(f"   ✓ Team slug generated: {new_team.slug}")
            if new_team.color == '#2980b9':
                print("   ✓ Color saved correctly")
            if new_team.icon == 'rocket':
                print("   ✓ Icon saved correctly")

            # Check if creator is added as team lead
            membership = TeamMembership.objects.filter(
                team=new_team, user=staff_user, role='lead'
            ).first()
            if membership:
                print("   ✓ Creator auto-added as team lead")
            else:
                print("   ✗ Creator not added as team lead")
        else:
            print("   ✗ Team not found after creation")
    else:
        print(f"   ✗ Team not created (status: {response.status_code})")

    # Test 5: Slug uniqueness
    print("\n5. Testing slug uniqueness...")
    response = client.post(reverse('teams:team-create'), {
        'name': 'New Test Team',
        'description': 'Another team with same name',
        'color': '#6366f1',
        'icon': 'star'
    })
    duplicate_teams = Team.objects.filter(name='New Test Team')
    if duplicate_teams.count() > 1:
        slugs = [t.slug for t in duplicate_teams]
        if len(slugs) == len(set(slugs)):
            print(f"   ✓ Unique slugs generated: {slugs}")
        else:
            print("   ✗ Slugs are not unique")

    client.logout()


def test_user_assignment_view():
    """Test user assignment functionality."""
    print("\n" + "="*60)
    print("Testing User Assignment")
    print("="*60)

    staff_user, regular_user, user2, test_team = setup_test_data()
    client = Client()

    # Test 1: Non-staff cannot access user list
    print("\n1. Testing non-staff cannot access user list...")
    client.login(username='test_regular', password='testpass123')
    response = client.get(reverse('teams:team-user-list'))
    if response.status_code == 403:
        print("   ✓ Non-staff user correctly denied (403)")
    else:
        print(f"   ✗ Expected 403, got {response.status_code}")
    client.logout()

    # Test 2: Staff can access user list
    print("\n2. Testing staff can access user list...")
    client.login(username='test_staff', password='testpass123')
    response = client.get(reverse('teams:team-user-list'))
    if response.status_code == 200:
        print("   ✓ Staff user can access user list (200)")
        if 'users' in response.context:
            users_count = len(response.context['users'])
            print(f"   ✓ Users list provided ({users_count} users)")
        if 'all_teams' in response.context:
            print("   ✓ All teams provided in context")
    else:
        print(f"   ✗ Expected 200, got {response.status_code}")

    # Test 3: Search functionality
    print("\n3. Testing search functionality...")
    response = client.get(reverse('teams:team-user-list'), {'q': 'regular'})
    if response.status_code == 200:
        if 'users' in response.context:
            filtered_users = response.context['users']
            if any('regular' in u.username.lower() or 'regular' in u.display_name.lower()
                   for u in filtered_users):
                print("   ✓ Search filters users correctly")
            else:
                print("   ✗ Search did not filter correctly")

    # Test 4: Assign user to team
    print("\n4. Testing assign user to team...")
    initial_memberships = TeamMembership.objects.filter(user=regular_user).count()
    response = client.post(
        reverse('teams:team-user-assign', args=[regular_user.pk]),
        {
            'team_id': test_team.pk,
            'role': 'member'
        }
    )
    new_memberships = TeamMembership.objects.filter(user=regular_user).count()

    if new_memberships > initial_memberships:
        print("   ✓ User assigned to team successfully")
        membership = TeamMembership.objects.filter(
            user=regular_user, team=test_team
        ).first()
        if membership and membership.role == 'member':
            print("   ✓ Role set correctly")
    else:
        print(f"   ✗ User not assigned (status: {response.status_code})")

    # Test 5: Remove user from team
    print("\n5. Testing remove user from team...")
    # Ensure user is in team first
    TeamMembership.objects.get_or_create(
        user=user2, team=test_team, defaults={'role': 'member'}
    )

    response = client.post(
        reverse('teams:team-user-remove', args=[user2.pk, test_team.slug])
    )

    membership_exists = TeamMembership.objects.filter(
        user=user2, team=test_team
    ).exists()

    if not membership_exists:
        print("   ✓ User removed from team successfully")
    else:
        print(f"   ✗ User not removed (status: {response.status_code})")

    # Test 6: POST without team_id returns bad request
    print("\n6. Testing POST without team_id...")
    response = client.post(
        reverse('teams:team-user-assign', args=[regular_user.pk]),
        {'role': 'member'}
    )
    if response.status_code == 400:
        print("   ✓ Missing team_id correctly returns 400")
    else:
        print(f"   ✗ Expected 400, got {response.status_code}")

    client.logout()


def test_templates_exist():
    """Test that all required templates exist."""
    print("\n" + "="*60)
    print("Testing Templates")
    print("="*60)

    from django.template.loader import get_template

    templates = [
        'teams/create.html',
        'teams/user_list.html',
        'teams/partials/user_team_badges.html',
    ]

    for template_name in templates:
        try:
            template = get_template(template_name)
            print(f"✓ {template_name:40} exists")
        except Exception as e:
            print(f"✗ {template_name:40} ERROR: {e}")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*60)
    print("ISSUE-16 Acceptance Criteria Tests")
    print("Feature: Team Creation & User Assignment (Staff only)")
    print("="*60)

    try:
        test_url_patterns()
        test_templates_exist()
        test_team_create_view()
        test_user_assignment_view()

        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
