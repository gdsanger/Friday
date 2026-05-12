"""
Test for issue: ProgrammingError - column teams_team.is_global does not exist

This test verifies that the is_global field exists in the Team model and can be used
in templates and queries without raising ProgrammingError.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.teams.models import Team

User = get_user_model()


class TeamsIsGlobalFieldTest(TestCase):
    """Test that the is_global field exists and works correctly."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_team_model_has_is_global_field(self):
        """Test that Team model has is_global field."""
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            is_global=True
        )
        self.assertTrue(hasattr(team, 'is_global'))
        self.assertTrue(team.is_global)

    def test_teams_list_view_renders_without_error(self):
        """Test that teams list view renders without ProgrammingError."""
        # Create a global team
        Team.objects.create(
            name='Global Team',
            slug='global-team',
            is_global=True
        )

        # Create a non-global team
        Team.objects.create(
            name='Regular Team',
            slug='regular-team',
            is_global=False
        )

        # Request the teams list page
        response = self.client.get('/teams/')

        # Check that the page loads without error
        self.assertEqual(response.status_code, 200)

        # Check that the response contains expected content
        self.assertContains(response, 'Global Team')
        self.assertContains(response, 'Regular Team')

    def test_teams_list_displays_global_badge(self):
        """Test that global teams display the globe icon."""
        # Create a global team
        Team.objects.create(
            name='Global Team',
            slug='global-team',
            is_global=True
        )

        response = self.client.get('/teams/')

        # Check for the globe icon that indicates global team
        self.assertContains(response, 'bi-globe2')
        self.assertContains(response, 'Global team')

    def test_query_teams_with_is_global_filter(self):
        """Test that we can filter teams by is_global field."""
        # Create teams
        global_team = Team.objects.create(
            name='Global Team',
            slug='global-team',
            is_global=True
        )
        regular_team = Team.objects.create(
            name='Regular Team',
            slug='regular-team',
            is_global=False
        )

        # Query global teams
        global_teams = Team.objects.filter(is_global=True)
        self.assertEqual(global_teams.count(), 1)
        self.assertEqual(global_teams.first().slug, 'global-team')

        # Query non-global teams
        regular_teams = Team.objects.filter(is_global=False)
        self.assertIn(regular_team, regular_teams)


if __name__ == '__main__':
    import sys
    from django.core.management import execute_from_command_line

    # Run the specific test
    sys.argv = ['manage.py', 'test', 'test_issue_teams_is_global_fix']
    execute_from_command_line(sys.argv)
