"""
Tests for Azure AD user pre-provisioning feature.
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.accounts.azure_directory import search_azure_users, get_azure_user
from apps.core.models import Client
from apps.teams.models import Team, TeamMembership

User = get_user_model()


class AzureDirectoryTests(TestCase):
    """Tests for Azure directory search functions."""

    @patch('apps.accounts.azure_directory.MailService._get_token')
    @patch('apps.accounts.azure_directory.httpx.Client')
    def test_search_azure_users_success(self, mock_client, mock_get_token):
        """Test successful Azure user search."""
        mock_get_token.return_value = 'fake-token'

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {
                    'id': 'oid-123',
                    'displayName': 'John Doe',
                    'mail': 'john.doe@example.com',
                    'userPrincipalName': 'john.doe@example.com',
                    'jobTitle': 'Developer',
                    'department': 'Engineering',
                }
            ]
        }

        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        results = search_azure_users('john')

        assert len(results) == 1
        assert results[0]['azure_oid'] == 'oid-123'
        assert results[0]['name'] == 'John Doe'
        assert results[0]['email'] == 'john.doe@example.com'
        assert results[0]['job_title'] == 'Developer'

    def test_search_azure_users_short_query(self):
        """Test that short queries return empty list."""
        results = search_azure_users('a')
        assert results == []

        results = search_azure_users('')
        assert results == []

    @patch('apps.accounts.azure_directory.MailService._get_token')
    @patch('apps.accounts.azure_directory.httpx.Client')
    def test_search_azure_users_api_error(self, mock_client, mock_get_token):
        """Test handling of API errors."""
        mock_get_token.return_value = 'fake-token'

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Server error'

        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        results = search_azure_users('john')
        assert results == []

    @patch('apps.accounts.azure_directory.MailService._get_token')
    @patch('apps.accounts.azure_directory.httpx.Client')
    def test_search_azure_users_filter_syntax(self, mock_client, mock_get_token):
        """Test that Graph API $filter syntax is correct (not $search with colons)."""
        mock_get_token.return_value = 'fake-token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'value': []}

        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        search_azure_users('angermeier')

        # Verify the API was called with correct $filter syntax
        call_args = mock_client_instance.get.call_args
        params = call_args[1]['params']

        # Should use $filter with startswith(), not $search with colons
        assert '$filter' in params
        assert '$search' not in params

        # Filter should use startswith() function with single quotes
        filter_value = params['$filter']
        assert "startswith(displayName,'angermeier')" in filter_value
        assert "startswith(mail,'angermeier')" in filter_value
        assert "startswith(userPrincipalName,'angermeier')" in filter_value

        # Should NOT contain the old broken syntax with colons
        assert ':' not in filter_value  # No colons in OData filter functions

    @patch('apps.accounts.azure_directory.MailService._get_token')
    @patch('apps.accounts.azure_directory.httpx.Client')
    def test_search_azure_users_escapes_single_quotes(self, mock_client, mock_get_token):
        """Test that single quotes in query are properly escaped for OData."""
        mock_get_token.return_value = 'fake-token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'value': []}

        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # Search for a name with a single quote (e.g., O'Brien)
        search_azure_users("o'brien")

        # Verify single quotes are doubled (OData escape syntax)
        call_args = mock_client_instance.get.call_args
        params = call_args[1]['params']
        filter_value = params['$filter']

        # Single quotes should be escaped by doubling them
        assert "o''brien" in filter_value

    @patch('apps.accounts.azure_directory.MailService._get_token')
    @patch('apps.accounts.azure_directory.httpx.Client')
    def test_get_azure_user_success(self, mock_client, mock_get_token):
        """Test successful single user retrieval."""
        mock_get_token.return_value = 'fake-token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'oid-123',
            'displayName': 'John Doe',
            'mail': 'john.doe@example.com',
            'userPrincipalName': 'john.doe@example.com',
            'jobTitle': 'Developer',
            'department': 'Engineering',
        }

        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        result = get_azure_user('oid-123')

        assert result is not None
        assert result['azure_oid'] == 'oid-123'
        assert result['name'] == 'John Doe'


@pytest.mark.django_db
class UserInviteViewTests(TestCase):
    """Tests for user invitation views."""

    def setUp(self):
        """Set up test client and staff user."""
        self.client = TestClient()
        self.staff_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True,
        )
        self.staff_user.set_password('password')
        self.staff_user.save()

        self.team = Team.objects.create(
            name='Engineering',
            slug='engineering',
        )

        self.portal_client = Client.objects.create(
            name='Test Client',
            slug='test-client',
        )

    def test_user_invite_view_requires_staff(self):
        """Test that invitation page requires staff access."""
        url = reverse('admin_panel:admin-user-invite-azure')
        response = self.client.get(url)

        # Should redirect to login
        assert response.status_code == 302

    def test_user_invite_view_loads(self):
        """Test that invitation page loads for staff."""
        self.client.login(username='admin', password='password')
        url = reverse('admin_panel:admin-user-invite-azure')
        response = self.client.get(url)

        assert response.status_code == 200
        assert 'User einladen' in str(response.content)

    @patch('apps.admin_panel.views.search_azure_users')
    def test_user_invite_search_view(self, mock_search):
        """Test Azure user search endpoint."""
        self.client.login(username='admin', password='password')

        mock_search.return_value = [
            {
                'azure_oid': 'oid-123',
                'azure_upn': 'john.doe@example.com',
                'email': 'john.doe@example.com',
                'name': 'John Doe',
                'job_title': 'Developer',
                'department': 'Engineering',
            }
        ]

        url = reverse('admin_panel:admin-user-invite-search')
        response = self.client.get(url, {'q': 'john'})

        assert response.status_code == 200
        assert b'John Doe' in response.content
        assert b'john.doe@example.com' in response.content
        content = response.content.decode('utf-8')
        assert 'Verfügbar' in content

    @patch('apps.admin_panel.views.search_azure_users')
    def test_user_invite_search_marks_existing_users(self, mock_search):
        """Test that existing users are marked in search results."""
        self.client.login(username='admin', password='password')

        # Create existing user with azure_oid
        existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            azure_oid='oid-existing',
        )

        mock_search.return_value = [
            {
                'azure_oid': 'oid-existing',
                'azure_upn': 'existing@example.com',
                'email': 'existing@example.com',
                'name': 'Existing User',
                'job_title': 'Developer',
                'department': 'Engineering',
            },
            {
                'azure_oid': 'oid-new',
                'azure_upn': 'new@example.com',
                'email': 'new@example.com',
                'name': 'New User',
                'job_title': 'Designer',
                'department': 'Design',
            }
        ]

        url = reverse('admin_panel:admin-user-invite-search')
        response = self.client.get(url, {'q': 'user'})

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Bereits in Friday' in content
        assert 'Verfügbar' in content

    @patch('apps.admin_panel.views.get_azure_user')
    @patch('apps.mail.tasks.send_invitation_mail.delay')
    def test_user_provision_view_creates_friday_user(self, mock_send_mail, mock_get_user):
        """Test provisioning a Friday user."""
        self.client.login(username='admin', password='password')

        mock_get_user.return_value = {
            'azure_oid': 'oid-123',
            'azure_upn': 'john.doe@example.com',
            'email': 'john.doe@example.com',
            'name': 'John Doe',
            'job_title': 'Developer',
            'department': 'Engineering',
        }

        url = reverse('admin_panel:admin-user-provision')
        response = self.client.post(url, {
            'azure_oids[]': ['oid-123'],
            'user_type': 'friday',
            'team_ids[]': [str(self.team.pk)],
            'send_invite': '1',
        })

        assert response.status_code == 200

        # Check user was created
        user = User.objects.get(azure_oid='oid-123')
        assert user.username == 'john.doe'
        assert user.email == 'john.doe@example.com'
        assert user.display_name == 'John Doe'
        assert user.azure_upn == 'john.doe@example.com'
        assert user.is_active is True
        assert user.is_portal_user is False
        assert not user.has_usable_password()

        # Check team membership
        assert TeamMembership.objects.filter(user=user, team=self.team).exists()

        # Check invitation email was sent
        mock_send_mail.assert_called_once_with(user.pk)

    @patch('apps.admin_panel.views.get_azure_user')
    @patch('apps.mail.tasks.send_invitation_mail.delay')
    def test_user_provision_view_creates_portal_user(self, mock_send_mail, mock_get_user):
        """Test provisioning a Portal user."""
        self.client.login(username='admin', password='password')

        mock_get_user.return_value = {
            'azure_oid': 'oid-portal',
            'azure_upn': 'portal@example.com',
            'email': 'portal@example.com',
            'name': 'Portal User',
            'job_title': 'Customer',
            'department': '',
        }

        url = reverse('admin_panel:admin-user-provision')
        response = self.client.post(url, {
            'azure_oids[]': ['oid-portal'],
            'user_type': 'portal',
            'portal_client': str(self.portal_client.pk),
            'send_invite': '1',
        })

        assert response.status_code == 200

        # Check user was created
        user = User.objects.get(azure_oid='oid-portal')
        assert user.is_portal_user is True
        assert user.portal_client == self.portal_client

    @patch('apps.admin_panel.views.get_azure_user')
    def test_user_provision_skips_existing_users(self, mock_get_user):
        """Test that existing users are skipped."""
        self.client.login(username='admin', password='password')

        # Create existing user
        existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            azure_oid='oid-existing',
        )

        url = reverse('admin_panel:admin-user-provision')
        response = self.client.post(url, {
            'azure_oids[]': ['oid-existing'],
            'user_type': 'friday',
            'send_invite': '1',
        })

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'übersprungen' in content

        # Should not call get_azure_user for existing users
        mock_get_user.assert_not_called()

    def test_user_provision_generates_unique_usernames(self):
        """Test that usernames are unique even with duplicates."""
        self.client.login(username='admin', password='password')

        # Create existing user with same base username
        existing = User.objects.create_user(
            username='john.doe',
            email='existing@example.com',
        )

        with patch('apps.admin_panel.views.get_azure_user') as mock_get_user:
            mock_get_user.return_value = {
                'azure_oid': 'oid-new',
                'azure_upn': 'john.doe@newdomain.com',
                'email': 'john.doe@newdomain.com',
                'name': 'John Doe',
                'job_title': 'Developer',
                'department': '',
            }

            url = reverse('admin_panel:admin-user-provision')
            response = self.client.post(url, {
                'azure_oids[]': ['oid-new'],
                'user_type': 'friday',
                'send_invite': '0',
            })

            # Check new user has incremented username
            user = User.objects.get(azure_oid='oid-new')
            assert user.username == 'john.doe1'


@pytest.mark.django_db
class InvitationMailTests(TestCase):
    """Tests for invitation email."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            display_name='Test User',
            azure_oid='oid-test',
            azure_upn='test@example.com',
        )
        self.user.set_unusable_password()
        self.user.save()

    @patch('apps.mail.tasks.dispatch')
    def test_send_invitation_mail_friday_user(self, mock_dispatch):
        """Test sending invitation mail to Friday user."""
        from apps.mail.tasks import send_invitation_mail

        send_invitation_mail(self.user.pk)

        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args

        assert call_args[1]['event'] == 'user_invited'
        context = call_args[1]['context']
        assert context['recipient_name'] == 'Test User'
        assert '/accounts/azure/login/' in context['login_url']
        assert context['user_type'] == 'Friday'
        assert call_args[1]['recipients_override'] == ['test@example.com']

    @patch('apps.mail.tasks.dispatch')
    def test_send_invitation_mail_portal_user(self, mock_dispatch):
        """Test sending invitation mail to Portal user."""
        from apps.mail.tasks import send_invitation_mail

        # Create portal client
        client = Client.objects.create(name='Test Client', slug='test')
        self.user.is_portal_user = True
        self.user.portal_client = client
        self.user.save()

        send_invitation_mail(self.user.pk)

        mock_dispatch.assert_called_once()
        context = mock_dispatch.call_args[1]['context']
        assert context['user_type'] == 'Portal'
        assert context['portal_client'] == 'Test Client'
