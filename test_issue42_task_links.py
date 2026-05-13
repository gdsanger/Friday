"""
Test for ISSUE-42: Task links in project detail view

Acceptance Criteria:
- [ ] Task-Titel in der Projekt-Detail-Taskliste sind klickbar
- [ ] Klick öffnet Task-Slide-Over via HTMX
- [ ] URL aktualisiert sich auf `/tasks/<pk>/detail/`
- [ ] Direktaufruf der URL rendert Full-Detail-Seite (non-HTMX Fallback)
"""
import pytest
from django.test import Client, TestCase
from django.urls import reverse
from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.django_db
class TestTaskLinksInProjectDetail(TestCase):
    """Test task links with HTMX slide-over in project detail view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            owner=self.user,
            status='active'
        )

        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            created_by=self.user,
            status='todo'
        )

    def test_task_links_exist_in_project_detail(self):
        """Test that task titles in project detail are clickable links."""
        url = reverse('projects:project-detail', args=[self.project.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check that the task link is present with href
        task_detail_url = reverse('tasks:task-detail-full', args=[self.task.pk])
        assert f'href="{task_detail_url}"' in content, \
            "Task link should have href attribute for fallback"

    def test_task_links_have_htmx_attributes(self):
        """Test that task links have HTMX attributes for slide-over."""
        url = reverse('projects:project-detail', args=[self.project.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check for HTMX attributes
        task_detail_url = reverse('tasks:task-detail', args=[self.task.pk])
        assert f'hx-get="{task_detail_url}"' in content, \
            "Task link should have hx-get attribute"
        assert 'hx-target="#slide-over"' in content, \
            "Task link should target slide-over container"
        assert 'hx-swap="innerHTML"' in content, \
            "Task link should use innerHTML swap"
        assert 'hx-push-url="true"' in content, \
            "Task link should push URL to browser history"

    def test_slide_over_infrastructure_exists(self):
        """Test that slide-over containers exist in base template."""
        url = reverse('projects:project-detail', args=[self.project.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check for slide-over containers
        assert 'id="slide-over"' in content, \
            "Slide-over container should exist"
        assert 'id="slide-over-backdrop"' in content, \
            "Slide-over backdrop should exist"

    def test_htmx_request_returns_slide_over(self):
        """Test that HTMX request to task-detail returns slide-over content."""
        url = reverse('tasks:task-detail', args=[self.task.pk])
        response = self.client.get(
            url,
            HTTP_HX_REQUEST='true'  # Simulate HTMX request
        )

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Should contain slide-over specific elements
        assert 'slide-over' in content.lower(), \
            "HTMX request should return slide-over content"
        assert self.task.title in content, \
            "Slide-over should contain task title"

    def test_direct_url_returns_full_page(self):
        """Test that direct URL access returns full detail page (non-HTMX fallback)."""
        url = reverse('tasks:task-detail-full', args=[self.task.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Should be a full page with base template
        assert '<!DOCTYPE html>' in content or '<html' in content, \
            "Direct access should return full HTML page"
        assert self.task.title in content, \
            "Full page should contain task title"

    def test_multiple_tasks_all_have_links(self):
        """Test that all tasks in the list have clickable links."""
        # Create multiple tasks
        task2 = Task.objects.create(
            title='Second Task',
            project=self.project,
            created_by=self.user,
            status='in_progress'
        )
        task3 = Task.objects.create(
            title='Third Task',
            project=self.project,
            created_by=self.user,
            status='backlog'
        )

        url = reverse('projects:project-detail', args=[self.project.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check that all tasks have links
        for task in [self.task, task2, task3]:
            task_detail_url = reverse('tasks:task-detail', args=[task.pk])
            assert f'hx-get="{task_detail_url}"' in content, \
                f"Task '{task.title}' should have HTMX link"
            assert task.title in content, \
                f"Task '{task.title}' should be displayed"

    def test_task_link_styling(self):
        """Test that task links have proper styling."""
        url = reverse('projects:project-detail', args=[self.project.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check for styling classes/attributes
        assert 'text-decoration-none' in content, \
            "Task link should have no text decoration"
        assert 'fw-medium' in content, \
            "Task link should have medium font weight"
        assert 'var(--friday-text)' in content, \
            "Task link should use CSS variable for color"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
