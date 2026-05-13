#!/usr/bin/env python
"""
Test script to verify the fix for the template filter role exception.
This test verifies that:
1. The User.is_team_lead property works correctly
2. The dashboard template renders without template syntax errors
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ.setdefault('FIELD_ENCRYPTION_KEY', '9RpaVfMK_6gwyMBlycIzeKORhY5_iBCh53-uL4eK74I=')
os.environ.setdefault('DATABASE_URL', 'sqlite:////tmp/friday_test_filter_role.sqlite3')
django.setup()

from django.core.management import call_command
# Run migrations to create the database schema
call_command('migrate', interactive=False, verbosity=0)

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership

User = get_user_model()


def test_user_is_team_lead_property():
    """Test that User.is_team_lead property works correctly."""
    print("\n✓ Test 1: User.is_team_lead property")

    # Create a test user
    user = User.objects.create_user(
        username='test_lead_user',
        email='lead@example.com',
        password='testpass123'
    )

    # User should not be a team lead initially
    assert user.is_team_lead == False, "User should not be a team lead initially"
    print("  ✓ User is not a team lead initially")

    # Create a team and add user as a member (not lead)
    team = Team.objects.create(
        name='Test Team',
        slug='test-team',
        description='Test team'
    )

    membership = TeamMembership.objects.create(
        user=user,
        team=team,
        role=TeamMembership.ROLE_MEMBER
    )

    # User should still not be a team lead
    assert user.is_team_lead == False, "User should not be a team lead with member role"
    print("  ✓ User is not a team lead with member role")

    # Change membership to lead role
    membership.role = TeamMembership.ROLE_LEAD
    membership.save()

    # User should now be a team lead
    assert user.is_team_lead == True, "User should be a team lead with lead role"
    print("  ✓ User is a team lead with lead role")

    # Clean up
    membership.delete()
    team.delete()
    user.delete()

    print("  ✓ All assertions passed")


def test_dashboard_renders_without_error():
    """Test that the dashboard template renders without template syntax errors."""
    print("\n✓ Test 2: Dashboard template renders without errors")

    # Create a test user with staff privileges
    staff_user = User.objects.create_user(
        username='test_staff_user',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )

    # Test with staff user
    client = Client()
    client.force_login(staff_user)

    response = client.get('/dashboard/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("  ✓ Dashboard renders with status 200 for staff user")

    # Create a regular user who is a team lead
    lead_user = User.objects.create_user(
        username='test_lead_user2',
        email='lead2@example.com',
        password='testpass123'
    )

    team = Team.objects.create(
        name='Test Team 2',
        slug='test-team-2',
        description='Test team 2'
    )

    TeamMembership.objects.create(
        user=lead_user,
        team=team,
        role=TeamMembership.ROLE_LEAD
    )

    # Test with team lead user
    client.force_login(lead_user)
    response = client.get('/dashboard/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("  ✓ Dashboard renders with status 200 for team lead user")

    # Create a regular user who is not a lead
    member_user = User.objects.create_user(
        username='test_member_user',
        email='member@example.com',
        password='testpass123'
    )

    TeamMembership.objects.create(
        user=member_user,
        team=team,
        role=TeamMembership.ROLE_MEMBER
    )

    # Test with regular member user
    client.force_login(member_user)
    response = client.get('/dashboard/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("  ✓ Dashboard renders with status 200 for regular member user")

    # Clean up
    staff_user.delete()
    lead_user.delete()
    member_user.delete()
    team.delete()

    print("  ✓ All dashboard rendering tests passed")


def run_tests():
    """Run all tests."""
    print("=" * 80)
    print("Fix Filter Role Exception Tests")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    try:
        test_user_is_team_lead_property()
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ Test failed: {e}")
        tests_failed += 1
    except Exception as e:
        print(f"  ✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    try:
        test_dashboard_renders_without_error()
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ Test failed: {e}")
        tests_failed += 1
    except Exception as e:
        print(f"  ✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 80)

    if tests_failed == 0:
        print("\n✓ All tests PASSED!")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
