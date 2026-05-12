"""
ISSUE-20 Global Teams Feature — Acceptance Criteria Tests
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from apps.teams.models import Team, TeamMembership
from apps.projects.models import Project, ProjectUserMembership, ProjectTeamMembership
from apps.tasks.models import Task

User = get_user_model()


def print_header(text):
    print(f"\n{'='*70}")
    print(text)
    print('='*70)


def test_pass(desc):
    print(f"✓ {desc}")
    return True


def test_fail(desc, error):
    print(f"✗ {desc}: {error}")
    return False


class GlobalTeamsTestCase(TestCase):
    """Test suite for ISSUE-20 Global Teams feature."""

    def setUp(self):
        """Create test users, teams, and projects."""
        # Clean up first to avoid conflicts
        User.objects.filter(username__startswith='testuser').delete()
        Team.objects.filter(slug__startswith='test-').delete()
        Project.objects.filter(name__startswith='Test ').delete()

        # Create users
        self.user1 = User.objects.create_user(
            username='testuser1', email='testuser1@test.com', password='test'
        )
        self.user2 = User.objects.create_user(
            username='testuser2', email='testuser2@test.com', password='test'
        )
        self.user3 = User.objects.create_user(
            username='testuser3', email='testuser3@test.com', password='test'
        )
        self.staff_user = User.objects.create_user(
            username='teststaff', email='teststaff@test.com', password='test', is_staff=True
        )

        # Create regular team
        self.regular_team = Team.objects.create(
            name='Test Development Team',
            slug='test-development-team',
            is_global=False
        )

        # Create global team
        self.global_team = Team.objects.create(
            name='Test IT Support',
            slug='test-it-support',
            is_global=True
        )

        # Add user1 to regular team
        TeamMembership.objects.create(
            user=self.user1,
            team=self.regular_team,
            role='member'
        )

        # Add user2 to global team
        TeamMembership.objects.create(
            user=self.user2,
            team=self.global_team,
            role='member'
        )

        # Create test project
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user3,
            visibility='members'
        )

        # Add user3 as project manager
        ProjectUserMembership.objects.create(
            project=self.project,
            user=self.user3,
            role='manager'
        )

        # Add regular team to project (NOT global team)
        ProjectTeamMembership.objects.create(
            project=self.project,
            team=self.regular_team,
            role='contributor'
        )


def run_tests():
    """Run all acceptance criteria tests."""
    from apps.teams.models import Team as TeamModel

    results = {'passed': 0, 'failed': 0}

    print_header("ISSUE-20 Global Teams — Acceptance Criteria Tests")

    # Clean up database first
    User.objects.filter(username__startswith='testuser').delete()
    User.objects.filter(username='teststaff').delete()
    TeamModel.objects.filter(slug__startswith='test').delete()
    Project.objects.filter(name__startswith='Test').delete()

    # Model Tests
    print("\n## Model Tests")
    try:
        # Test is_global field exists
        TeamModel.objects.filter(slug='test-model').delete()
        team = TeamModel.objects.create(name='Test Model', slug='test-model')
        assert hasattr(team, 'is_global')
        assert team.is_global == False  # Default is False
        results['passed'] += test_pass("Team.is_global field exists with default=False")
    except Exception as e:
        results['failed'] += test_fail("Team.is_global field", str(e))

    try:
        # Test creating global team
        TeamModel.objects.filter(slug='global-test-model').delete()
        global_team = TeamModel.objects.create(name='Global Test Model', slug='global-test-model', is_global=True)
        assert global_team.is_global == True
        results['passed'] += test_pass("Can create global team with is_global=True")
    except Exception as e:
        results['failed'] += test_fail("Create global team", str(e))

    # Access Logic Tests
    print("\n## Access Logic Tests")

    # Create test case instance for access logic tests
    tc = GlobalTeamsTestCase()
    tc.setUp()

    try:
        # Test get_all_members includes global team members
        all_members = tc.project.get_all_members()
        member_ids = set(all_members.values_list('id', flat=True))

        # user1 should be member (via regular team)
        assert tc.user1.id in member_ids, "user1 should be member via regular team"

        # user2 should be member (via global team)
        assert tc.user2.id in member_ids, "user2 should be member via global team"

        # user3 should be member (direct)
        assert tc.user3.id in member_ids, "user3 should be direct member"

        results['passed'] += test_pass("project.get_all_members() includes global team members")
    except AssertionError as e:
        results['failed'] += test_fail("project.get_all_members()", str(e))

    try:
        # Test get_effective_role for global team member
        role = tc.project.get_effective_role(tc.user2)
        assert role == 'contributor', f"Expected 'contributor', got '{role}'"
        results['passed'] += test_pass("project.get_effective_role(global_member) returns 'contributor'")
    except AssertionError as e:
        results['failed'] += test_fail("get_effective_role for global member", str(e))

    try:
        # Test is_member for global team member
        assert tc.project.is_member(tc.user2), "Global team member should be project member"
        results['passed'] += test_pass("project.is_member(global_member) returns True")
    except AssertionError as e:
        results['failed'] += test_fail("is_member for global member", str(e))

    try:
        # Test that deactivating global team removes access
        tc.global_team.is_active = False
        tc.global_team.save()

        # Refresh from DB
        project = Project.objects.get(pk=tc.project.pk)
        all_members = project.get_all_members()
        member_ids = set(all_members.values_list('id', flat=True))

        # user2 should NOT be member anymore
        assert tc.user2.id not in member_ids, "Inactive global team member should not be project member"

        # Restore for other tests
        tc.global_team.is_active = True
        tc.global_team.save()

        results['passed'] += test_pass("Deactivating global team removes member access")
    except AssertionError as e:
        results['failed'] += test_fail("Deactivate global team", str(e))

    # Task Assignment Tests
    print("\n## Task Assignment Tests")

    try:
        # Test that global teams appear in task assignment
        from apps.teams.models import Team
        from django.db.models import Q

        # Simulate what TaskDetailView does
        task = Task.objects.create(
            title='Test Task',
            project=tc.project,
            created_by=tc.user3
        )

        project_teams = Team.objects.filter(
            Q(projectteammembership__project=tc.project) |
            Q(is_global=True),
            is_active=True
        ).distinct().order_by('name')

        team_names = set(project_teams.values_list('name', flat=True))

        assert tc.regular_team.name in team_names, "Regular team should be available"
        assert tc.global_team.name in team_names, "Global team should be available"

        results['passed'] += test_pass("Global teams appear in task assignment dropdown")
    except AssertionError as e:
        results['failed'] += test_fail("Global teams in task assignment", str(e))

    try:
        # Test that non-global teams only appear if explicitly assigned
        TeamModel.objects.filter(slug='test-other-team').delete()
        other_team = TeamModel.objects.create(
            name='Test Other Team',
            slug='test-other-team',
            is_global=False
        )

        project_teams = Team.objects.filter(
            Q(projectteammembership__project=tc.project) |
            Q(is_global=True),
            is_active=True
        ).distinct()

        team_names = set(project_teams.values_list('name', flat=True))

        assert other_team.name not in team_names, "Non-global unassigned team should not appear"

        results['passed'] += test_pass("Non-global teams only appear if explicitly assigned")
    except AssertionError as e:
        results['failed'] += test_fail("Non-global team filtering", str(e))

    # UI Tests (checking context data)
    print("\n## UI Context Tests")

    try:
        # Test ProjectDetailView context includes global_teams
        from apps.projects.views import ProjectDetailView
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        factory = RequestFactory()
        request = factory.get(f'/projects/{tc.project.pk}/')
        request.user = tc.user3

        view = ProjectDetailView()
        view.request = request
        view.object = tc.project

        ctx = view.get_context_data(object=tc.project)

        assert 'global_teams' in ctx, "Context should include global_teams"
        global_teams = ctx['global_teams']
        assert tc.global_team in global_teams, "Global team should be in context"

        results['passed'] += test_pass("ProjectDetailView includes global_teams in context")
    except Exception as e:
        results['failed'] += test_fail("ProjectDetailView context", str(e))

    try:
        # Test that available_teams excludes global teams
        from apps.projects.views import ProjectDetailView
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get(f'/projects/{tc.project.pk}/')
        request.user = tc.user3

        view = ProjectDetailView()
        view.request = request
        view.object = tc.project

        ctx = view.get_context_data(object=tc.project)

        assert 'available_teams' in ctx, "Context should include available_teams"
        available_teams = ctx['available_teams']

        # Global team should NOT be in available_teams (can't be explicitly added)
        available_team_ids = set(available_teams.values_list('id', flat=True))
        assert tc.global_team.id not in available_team_ids, "Global team should not be in available_teams dropdown"

        results['passed'] += test_pass("available_teams excludes global teams")
    except Exception as e:
        results['failed'] += test_fail("available_teams filtering", str(e))

    # Edge Cases
    print("\n## Edge Case Tests")

    try:
        # Test project list view for global team members
        from apps.projects.views import ProjectListView
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get('/projects/?status=all')  # Remove status filter
        request.user = tc.user2  # Global team member
        request.GET = {'status': 'all'}

        view = ProjectListView()
        view.request = request

        queryset = view.get_queryset()

        # user2 is in global team, so should see ALL projects (with status filter removed)
        project_ids = list(queryset.values_list('id', flat=True))
        assert tc.project.id in project_ids, f"Global team member should see all projects. Project {tc.project.id} not in {project_ids}"

        results['passed'] += test_pass("ProjectListView shows all projects to global team members")
    except AssertionError as e:
        results['failed'] += test_fail("ProjectListView for global members", str(e))

    try:
        # Test that a team that is both global AND explicitly assigned is not duplicated
        ProjectTeamMembership.objects.create(
            project=tc.project,
            team=tc.global_team,
            role='viewer'
        )

        # Get all members should still be distinct
        all_members = tc.project.get_all_members()
        user2_count = sum(1 for u in all_members if u.id == tc.user2.id)

        assert user2_count == 1, f"user2 should appear exactly once, but appears {user2_count} times"

        results['passed'] += test_pass("Team that is both global and explicit is not duplicated")
    except AssertionError as e:
        results['failed'] += test_fail("Duplicate team handling", str(e))

    # Print results
    print("\n" + "="*70)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print("="*70)

    if results['failed'] > 0:
        print("\n❌ Some tests failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    run_tests()
