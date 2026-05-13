"""
Comprehensive acceptance tests for Customer Portal (ISSUE-28).
Tests all acceptance criteria and user flows.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.core.models import Client as ClientModel
from apps.projects.models import Project
from apps.tasks.models import Task, TaskTemplate, Comment, Attachment
from apps.teams.models import Team

User = get_user_model()


@pytest.mark.django_db
class TestPortalAuth:
    """Test portal user authentication and routing."""

    def test_portal_user_redirected_to_portal_home(self, client, django_user_model):
        """Portal users should be redirected to /portal/ after login."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            password='testpass123',
            is_portal_user=True
        )

        response = client.post(reverse('accounts:login'), {
            'username': 'portal_user',
            'password': 'testpass123'
        })

        assert response.status_code == 302
        assert response.url == reverse('portal-home')

    def test_regular_user_redirected_to_dashboard(self, client, django_user_model):
        """Regular users should be redirected to /dashboard/ after login."""
        user = django_user_model.objects.create_user(
            username='regular_user',
            email='regular@test.com',
            password='testpass123',
            is_portal_user=False
        )

        response = client.post(reverse('accounts:login'), {
            'username': 'regular_user',
            'password': 'testpass123'
        })

        assert response.status_code == 302
        assert '/dashboard/' in response.url

    def test_portal_middleware_blocks_dashboard_access(self, client, django_user_model):
        """Portal users should not be able to access /dashboard/."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            password='testpass123',
            is_portal_user=True
        )
        client.force_login(user)

        response = client.get('/dashboard/')

        assert response.status_code == 302
        assert response.url == reverse('portal-home')

    def test_portal_middleware_blocks_kanban_access(self, client, django_user_model):
        """Portal users should not be able to access /kanban/."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            password='testpass123',
            is_portal_user=True
        )
        client.force_login(user)

        response = client.get('/kanban/')

        assert response.status_code == 302
        assert response.url == reverse('portal-home')

    def test_regular_user_cannot_access_portal(self, client, django_user_model):
        """Regular users should get 403 when accessing /portal/."""
        user = django_user_model.objects.create_user(
            username='regular_user',
            email='regular@test.com',
            password='testpass123',
            is_portal_user=False
        )
        client.force_login(user)

        response = client.get(reverse('portal-home'))

        assert response.status_code == 403


@pytest.mark.django_db
class TestPortalTemplateSelection:
    """Test template selection for portal users."""

    def test_global_templates_visible(self, client, django_user_model):
        """Global templates (client=None) should be visible to all portal users."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Global Template',
            slug='global-template',
            is_active=True,
            is_portal_visible=True,
            client=None,
            default_project=project,
            default_priority=2
        )

        response = client.get(reverse('portal-template-select'))

        assert response.status_code == 200
        assert 'Global Template' in response.content.decode()

    def test_client_specific_templates_visible(self, client, django_user_model):
        """Templates with matching client should be visible."""
        test_client = ClientModel.objects.create(name='Test Client', slug='test-client')
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True,
            portal_client=test_client
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Client Template',
            slug='client-template',
            is_active=True,
            is_portal_visible=True,
            client=test_client,
            default_project=project,
            default_priority=2
        )

        response = client.get(reverse('portal-template-select'))

        assert response.status_code == 200
        assert 'Client Template' in response.content.decode()

    def test_other_client_templates_not_visible(self, client, django_user_model):
        """Templates for other clients should not be visible."""
        client1 = ClientModel.objects.create(name='Client 1', slug='client-1')
        client2 = ClientModel.objects.create(name='Client 2', slug='client-2')

        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True,
            portal_client=client1
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Client 2 Template',
            slug='client2-template',
            is_active=True,
            is_portal_visible=True,
            client=client2,
            default_project=project
        )

        response = client.get(reverse('portal-template-select'))

        assert response.status_code == 200
        assert 'Client 2 Template' not in response.content.decode()

    def test_non_portal_visible_templates_hidden(self, client, django_user_model):
        """Templates with is_portal_visible=False should not be visible."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Internal Template',
            slug='internal-template',
            is_active=True,
            is_portal_visible=False,
            client=None,
            default_project=project
        )

        response = client.get(reverse('portal-template-select'))

        assert response.status_code == 200
        assert 'Internal Template' not in response.content.decode()

    def test_empty_state_when_no_templates(self, client, django_user_model):
        """Empty state should be shown when no templates available."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        response = client.get(reverse('portal-template-select'))

        assert response.status_code == 200
        assert 'keine Anfragetypen verfügbar' in response.content.decode()


@pytest.mark.django_db
class TestPortalTicketCreation:
    """Test ticket creation from portal."""

    def test_create_ticket_with_valid_template(self, client, django_user_model):
        """Portal user should be able to create ticket from valid template."""
        test_client = ClientModel.objects.create(name='Test Client', slug='test-client')
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True,
            portal_client=test_client
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Test Template',
            slug='test-template',
            is_active=True,
            is_portal_visible=True,
            client=None,
            default_project=project,
            default_priority=2
        )

        response = client.post(reverse('portal-ticket-create', args=[template.slug]), {
            'title': 'Test Ticket',
            'description': 'Test description',
            'priority': 2,
        })

        assert response.status_code == 302
        task = Task.objects.get(title='Test Ticket')
        assert task.requester == user
        assert task.created_by == user
        assert task.client == test_client
        assert task.project == project
        assert task.template == template

    def test_title_required(self, client, django_user_model):
        """Title should be required when creating ticket."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Test Template',
            slug='test-template',
            is_active=True,
            is_portal_visible=True,
            default_project=project
        )

        response = client.post(reverse('portal-ticket-create', args=[template.slug]), {
            'title': '',
            'description': 'Test description',
        })

        assert response.status_code == 200
        assert 'Titel ist ein Pflichtfeld' in response.content.decode()
        assert Task.objects.count() == 0

    def test_cannot_access_other_client_template(self, client, django_user_model):
        """Portal user should not be able to use template for other client."""
        client1 = ClientModel.objects.create(name='Client 1', slug='client-1')
        client2 = ClientModel.objects.create(name='Client 2', slug='client-2')

        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True,
            portal_client=client1
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        template = TaskTemplate.objects.create(
            name='Client 2 Template',
            slug='client2-template',
            is_active=True,
            is_portal_visible=True,
            client=client2,
            default_project=project
        )

        response = client.get(reverse('portal-ticket-create', args=[template.slug]))

        assert response.status_code == 403


@pytest.mark.django_db
class TestPortalTicketList:
    """Test ticket list view for portal users."""

    def test_see_own_tickets_only(self, client, django_user_model):
        """Portal users should only see their own tickets."""
        user1 = django_user_model.objects.create_user(
            username='portal_user1',
            email='portal1@test.com',
            is_portal_user=True
        )
        user2 = django_user_model.objects.create_user(
            username='portal_user2',
            email='portal2@test.com',
            is_portal_user=True
        )

        project = Project.objects.create(name='Test Project')
        task1 = Task.objects.create(
            title='User 1 Task',
            project=project,
            created_by=user1,
            requester=user1
        )
        task2 = Task.objects.create(
            title='User 2 Task',
            project=project,
            created_by=user2,
            requester=user2
        )

        client.force_login(user1)
        response = client.get(reverse('portal-tickets'))

        assert response.status_code == 200
        content = response.content.decode()
        assert 'User 1 Task' in content
        assert 'User 2 Task' not in content

    def test_status_filter_works(self, client, django_user_model):
        """Status filter should work correctly."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        task1 = Task.objects.create(
            title='Backlog Task',
            project=project,
            created_by=user,
            requester=user,
            status=Task.STATUS_BACKLOG
        )
        task2 = Task.objects.create(
            title='Done Task',
            project=project,
            created_by=user,
            requester=user,
            status='done'
        )

        response = client.get(reverse('portal-tickets') + '?status=backlog')

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Backlog Task' in content

    def test_pagination_works(self, client, django_user_model):
        """Pagination should work for more than 20 tickets."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        for i in range(25):
            Task.objects.create(
                title=f'Task {i}',
                project=project,
                created_by=user,
                requester=user
            )

        response = client.get(reverse('portal-tickets'))

        assert response.status_code == 200
        assert 'pagination' in response.content.decode().lower() or 'page' in response.content.decode().lower()


@pytest.mark.django_db
class TestPortalTicketDetail:
    """Test ticket detail view for portal users."""

    def test_view_own_ticket(self, client, django_user_model):
        """Portal user should be able to view their own ticket."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        task = Task.objects.create(
            title='My Task',
            description='Test description',
            project=project,
            created_by=user,
            requester=user
        )

        response = client.get(reverse('portal-ticket-detail', args=[task.pk]))

        assert response.status_code == 200
        assert 'My Task' in response.content.decode()
        assert 'Test description' in response.content.decode()

    def test_cannot_view_other_user_ticket(self, client, django_user_model):
        """Portal user should not be able to view other users' tickets."""
        user1 = django_user_model.objects.create_user(
            username='portal_user1',
            email='portal1@test.com',
            is_portal_user=True
        )
        user2 = django_user_model.objects.create_user(
            username='portal_user2',
            email='portal2@test.com',
            is_portal_user=True
        )

        project = Project.objects.create(name='Test Project')
        task = Task.objects.create(
            title='User 2 Task',
            project=project,
            created_by=user2,
            requester=user2
        )

        client.force_login(user1)
        response = client.get(reverse('portal-ticket-detail', args=[task.pk]))

        assert response.status_code == 404

    def test_add_comment(self, client, django_user_model):
        """Portal user should be able to add comments to their tickets."""
        user = django_user_model.objects.create_user(
            username='portal_user',
            email='portal@test.com',
            is_portal_user=True
        )
        client.force_login(user)

        project = Project.objects.create(name='Test Project')
        task = Task.objects.create(
            title='My Task',
            project=project,
            created_by=user,
            requester=user
        )

        response = client.post(reverse('portal-ticket-comment', args=[task.pk]), {
            'body': 'Test comment'
        })

        assert response.status_code == 200
        assert Comment.objects.filter(task=task, author=user, body='Test comment').exists()


@pytest.mark.django_db
class TestAdminPortalManagement:
    """Test admin panel portal user management."""

    def test_admin_can_set_portal_user(self, client, django_user_model):
        """Staff users should be able to set portal_user flag."""
        admin = django_user_model.objects.create_user(
            username='admin',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        user = django_user_model.objects.create_user(
            username='user',
            email='user@test.com'
        )
        client.force_login(admin)

        response = client.post(reverse('admin_panel:admin-user-portal', args=[user.pk]), {
            'is_portal_user': 'on',
        })

        user.refresh_from_db()
        assert user.is_portal_user == True

    def test_admin_can_set_portal_client(self, client, django_user_model):
        """Staff users should be able to assign portal client."""
        admin = django_user_model.objects.create_user(
            username='admin',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        user = django_user_model.objects.create_user(
            username='user',
            email='user@test.com'
        )
        test_client = ClientModel.objects.create(name='Test Client', slug='test-client')
        client.force_login(admin)

        response = client.post(reverse('admin_panel:admin-user-portal', args=[user.pk]), {
            'is_portal_user': 'on',
            'portal_client': test_client.pk,
        })

        user.refresh_from_db()
        assert user.is_portal_user == True
        assert user.portal_client == test_client


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
