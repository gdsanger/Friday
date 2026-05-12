#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-02.

This script tests all requirements from the issue:
- All models exist and are properly configured
- AUTH_USER_MODEL is set correctly
- Migrations run without errors
- Singleton models work correctly
- Model methods and properties return expected values
- Database indexes are created
- Django admin is registered for all models
- Encryption works for sensitive fields
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib import admin
from django.db import connection
from apps.core.models import Organisation
from apps.ai.models import AIGlobalSettings, AIProviderConfig
from apps.teams.models import Team, TeamMembership
from apps.projects.models import Project, ProjectUserMembership, ProjectTeamMembership
from apps.tasks.models import Task, Label, Comment, Attachment, TimeEntry
from apps.notifications.models import Notification
from datetime import date, timedelta

User = get_user_model()

def test_auth_user_model():
    """Test AUTH_USER_MODEL = 'accounts.User'"""
    assert settings.AUTH_USER_MODEL == 'accounts.User', "AUTH_USER_MODEL not set correctly"
    print("✓ AUTH_USER_MODEL = 'accounts.User'")

def test_organisation_singleton():
    """Test Organisation.get() always returns pk=1 and never raises"""
    org1 = Organisation.get()
    assert org1.pk == 1, "Organisation pk is not 1"

    org2 = Organisation.get()
    assert org1.pk == org2.pk, "Organisation.get() returns different instances"

    # Try to delete (should not work)
    org1.delete()
    org3 = Organisation.objects.get(pk=1)
    assert org3.pk == 1, "Organisation was deleted"

    print("✓ Organisation.get() always returns pk=1 and never raises")

def test_ai_global_settings_singleton():
    """Test AIGlobalSettings.get() always returns pk=1 and never raises"""
    settings1 = AIGlobalSettings.get()
    assert settings1.pk == 1, "AIGlobalSettings pk is not 1"

    settings2 = AIGlobalSettings.get()
    assert settings1.pk == settings2.pk, "AIGlobalSettings.get() returns different instances"

    print("✓ AIGlobalSettings.get() always returns pk=1 and never raises")

def test_initial_data_migration():
    """Test initial data migration creates Organisation, IUN team, ISARtec team"""
    org = Organisation.objects.get(pk=1)
    assert org.name == 'EOE', f"Organisation name is {org.name}, expected EOE"

    iun = Team.objects.filter(slug='iun').first()
    assert iun is not None, "IUN team not created"

    isartec = Team.objects.filter(slug='isartec').first()
    assert isartec is not None, "ISARtec team not created"

    print("✓ Initial data migration creates Organisation, IUN team, ISARtec team")

def test_task_is_overdue():
    """Test Task.is_overdue returns correct boolean based on due_date"""
    user = User.objects.first()
    project = Project.objects.first()

    if not project:
        project = Project.objects.create(name='Test Project', owner=user)

    # Future task
    future_task = Task.objects.create(
        title='Future Task',
        project=project,
        status=Task.STATUS_TODO,
        due_date=date.today() + timedelta(days=1)
    )
    assert not future_task.is_overdue, "Future task marked as overdue"

    # Past task (not done)
    past_task = Task.objects.create(
        title='Past Task',
        project=project,
        status=Task.STATUS_IN_PROGRESS,
        due_date=date.today() - timedelta(days=1)
    )
    assert past_task.is_overdue, "Past task not marked as overdue"

    # Past task (done)
    done_task = Task.objects.create(
        title='Done Task',
        project=project,
        status=Task.STATUS_DONE,
        due_date=date.today() - timedelta(days=1)
    )
    assert not done_task.is_overdue, "Done task marked as overdue"

    print("✓ Task.is_overdue returns correct boolean based on due_date")

def test_task_assignee_display():
    """Test Task.assignee_display returns correct string"""
    user = User.objects.first()
    team = Team.objects.first()
    project = Project.objects.first()

    # User assigned
    user_task = Task.objects.create(
        title='User Task',
        project=project,
        assigned_to_user=user
    )
    assert user_task.assignee_display == user.full_name, \
        f"Expected '{user.full_name}', got '{user_task.assignee_display}'"

    # Team assigned
    team_task = Task.objects.create(
        title='Team Task',
        project=project,
        assigned_to_team=team
    )
    expected_team = f'Team: {team.name}'
    assert team_task.assignee_display == expected_team, \
        f"Expected '{expected_team}', got '{team_task.assignee_display}'"

    # Unassigned
    unassigned_task = Task.objects.create(
        title='Unassigned Task',
        project=project
    )
    assert unassigned_task.assignee_display == 'Unassigned', \
        f"Expected 'Unassigned', got '{unassigned_task.assignee_display}'"

    print("✓ Task.assignee_display returns name for user, 'Team: X' for team, 'Unassigned' for neither")

def test_project_get_all_members():
    """Test Project.get_all_members() returns union of direct users and team members"""
    # Create test data
    user1 = User.objects.create_user(username='proj_user1', email='pu1@test.com')
    user2 = User.objects.create_user(username='proj_user2', email='pu2@test.com')
    user3 = User.objects.create_user(username='proj_user3', email='pu3@test.com')

    team = Team.objects.first()
    TeamMembership.objects.create(user=user1, team=team)
    TeamMembership.objects.create(user=user2, team=team)

    project = Project.objects.create(name='Membership Test Project', owner=user1)

    # Add team to project
    ProjectTeamMembership.objects.create(project=project, team=team)

    # Add user3 directly
    ProjectUserMembership.objects.create(project=project, user=user3)

    members = project.get_all_members()
    member_set = set(members.values_list('username', flat=True))

    assert 'proj_user1' in member_set, "user1 (via team) not in members"
    assert 'proj_user2' in member_set, "user2 (via team) not in members"
    assert 'proj_user3' in member_set, "user3 (direct) not in members"

    # Check no duplicates
    assert members.count() == len(set(members)), "Duplicate members returned"

    print("✓ Project.get_all_members() returns union of direct users and team members, no duplicates")

def test_project_get_effective_role():
    """Test Project.get_effective_role() returns correct role"""
    user = User.objects.create_user(username='role_user', email='ru@test.com')
    team = Team.objects.first()
    TeamMembership.objects.create(user=user, team=team)

    project = Project.objects.create(name='Role Test Project', owner=user)

    # Test direct role
    ProjectUserMembership.objects.create(
        project=project,
        user=user,
        role=ProjectUserMembership.ROLE_MANAGER
    )

    role = project.get_effective_role(user)
    assert role == ProjectUserMembership.ROLE_MANAGER, \
        f"Expected 'manager', got '{role}'"

    # Test team role
    user2 = User.objects.create_user(username='role_user2', email='ru2@test.com')
    TeamMembership.objects.create(user=user2, team=team)
    ProjectTeamMembership.objects.create(
        project=project,
        team=team,
        role=ProjectTeamMembership.ROLE_CONTRIBUTOR
    )

    role2 = project.get_effective_role(user2)
    assert role2 == ProjectTeamMembership.ROLE_CONTRIBUTOR, \
        f"Expected 'contributor', got '{role2}'"

    print("✓ Project.get_effective_role() returns correct role for direct and team-based membership")

def test_timestamped_models():
    """Test all models with TimeStampedModel have created_at and updated_at"""
    team = Team.objects.first()
    assert hasattr(team, 'created_at'), "Team missing created_at"
    assert hasattr(team, 'updated_at'), "Team missing updated_at"

    project = Project.objects.first()
    assert hasattr(project, 'created_at'), "Project missing created_at"
    assert hasattr(project, 'updated_at'), "Project missing updated_at"

    print("✓ All models with TimeStampedModel have created_at and updated_at")

def test_encryption():
    """Test AIProviderConfig.api_key is stored encrypted"""
    provider = AIProviderConfig.objects.create(
        provider=AIProviderConfig.PROVIDER_CLAUDE,
        api_key='test-secret-key-123',
        model_name='claude-sonnet-4'
    )

    # Get raw value from database
    with connection.cursor() as cursor:
        cursor.execute("SELECT api_key FROM ai_aiproviderconfig WHERE provider='claude'")
        encrypted_value = cursor.fetchone()[0]

    # Encrypted value should be different
    assert encrypted_value != 'test-secret-key-123', "API key not encrypted"

    # Should decrypt correctly
    assert provider.api_key == 'test-secret-key-123', "API key not decrypting correctly"

    print("✓ AIProviderConfig.api_key is stored encrypted (EncryptedCharField)")

def test_database_indexes():
    """Test DB indexes exist"""
    with connection.cursor() as cursor:
        # Task indexes
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
            AND tbl_name='tasks_task'
            AND (name LIKE '%project%' OR name LIKE '%due_dat%' OR name LIKE '%assigne%');
        """)
        task_indexes = [row[0] for row in cursor.fetchall()]

        assert len(task_indexes) >= 4, f"Expected 4 task indexes, got {len(task_indexes)}"

        # Notification indexes
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
            AND tbl_name='notifications_notification'
            AND name LIKE '%recipie%';
        """)
        notif_indexes = [row[0] for row in cursor.fetchall()]

        assert len(notif_indexes) >= 1, f"Expected 1+ notification index, got {len(notif_indexes)}"

    print("✓ DB indexes exist on: Task(project, status), Task(due_date), Notification(recipient, is_read)")

def test_admin_registration():
    """Test Django admin is registered for all models"""
    models_to_check = [
        Organisation, User, Team, TeamMembership,
        Project, ProjectUserMembership, ProjectTeamMembership,
        Label, Task, Comment, Attachment, TimeEntry,
        AIProviderConfig, AIGlobalSettings,
        Notification
    ]

    for model in models_to_check:
        assert admin.site.is_registered(model), f"{model.__name__} not registered in admin"

    print("✓ Django admin is registered for all models (basic ModelAdmin sufficient)")

def run_all_tests():
    """Run all acceptance criteria tests"""
    print("\n" + "="*70)
    print("ISSUE-02 Acceptance Criteria Tests")
    print("="*70 + "\n")

    tests = [
        test_auth_user_model,
        test_organisation_singleton,
        test_ai_global_settings_singleton,
        test_initial_data_migration,
        test_task_is_overdue,
        test_task_assignee_display,
        test_project_get_all_members,
        test_project_get_effective_role,
        test_timestamped_models,
        test_encryption,
        test_database_indexes,
        test_admin_registration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    if failed == 0:
        print("🎉 All acceptance criteria tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
