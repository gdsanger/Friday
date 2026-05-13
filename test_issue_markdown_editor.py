"""
Test for markdown editor on task detail page (issue #20 / reference #91)
Tests that:
1. Task detail page loads correctly
2. Description field contains md-render class in view mode
3. Description field contains md-editor class in edit mode
4. Required JavaScript libraries are loaded in base template
"""
import pytest
from django.test import Client
from django.urls import reverse
from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.django_db
class TestMarkdownEditorOnTaskDetail:
    """Test markdown editor functionality on task detail page."""

    def test_task_detail_page_loads(self, client: Client, user: User, project: Project):
        """Test that the task detail page loads successfully."""
        # Create a task with markdown description
        task = Task.objects.create(
            title="Test Task with Markdown",
            description="## Heading\n\n**Bold text** and *italic text*",
            project=project,
            created_by=user,
            status='backlog'
        )

        # Login
        client.force_login(user)

        # Get task detail URL
        url = reverse('tasks:task-detail-full', args=[task.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert task.title.encode() in response.content

    def test_description_view_mode_has_md_render_class(self, client: Client, user: User, project: Project):
        """Test that description in view mode has md-render class for rendering."""
        task = Task.objects.create(
            title="Test Task",
            description="## Test Heading\n\nSome **bold** text",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)
        url = reverse('tasks:task-detail-full', args=[task.pk])
        response = client.get(url)

        # Check that md-render class is present in view mode
        assert b'class="md-render"' in response.content
        # Check that data-md attribute contains the description
        assert b'data-md=' in response.content

    def test_description_edit_mode_has_md_editor_class(self, client: Client, user: User, project: Project):
        """Test that description in edit mode has md-editor class for EasyMDE initialization."""
        task = Task.objects.create(
            title="Test Task",
            description="## Test Heading",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)

        # Get edit mode via TaskEditFieldView
        url = reverse('tasks:task-edit-field', args=[task.pk])
        response = client.get(url, {'mode': 'edit', 'field': 'description'})

        # Check that md-editor class is present for EasyMDE initialization
        assert b'md-editor' in response.content
        assert b'<textarea' in response.content

    def test_base_template_loads_markdown_libraries(self, client: Client, user: User, project: Project):
        """Test that base.html loads required markdown libraries."""
        task = Task.objects.create(
            title="Test Task",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)
        url = reverse('tasks:task-detail-full', args=[task.pk])
        response = client.get(url)

        # Check for EasyMDE CSS
        assert b'easymde.min.css' in response.content

        # Check for required JavaScript libraries
        assert b'easymde.min.js' in response.content
        assert b'marked.min.js' in response.content
        assert b'purify.min.js' in response.content or b'dompurify' in response.content.lower()

        # Check that friday.js is loaded
        assert b'friday.js' in response.content

    def test_description_field_partial_renders_correctly(self, client: Client, user: User, project: Project):
        """Test that the field_description.html partial renders with correct structure."""
        task = Task.objects.create(
            title="Test Task",
            description="Test description with markdown",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)

        # Test view mode
        url = reverse('tasks:task-edit-field', args=[task.pk])
        response = client.get(url, {'mode': 'view', 'field': 'description'})
        assert b'task-description' in response.content
        assert b'md-render' in response.content

        # Test edit mode
        response = client.get(url, {'mode': 'edit', 'field': 'description'})
        assert b'<form' in response.content
        assert b'md-editor' in response.content

    def test_empty_description_shows_placeholder(self, client: Client, user: User, project: Project):
        """Test that empty description shows placeholder text."""
        task = Task.objects.create(
            title="Test Task",
            description="",  # Empty description
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)
        url = reverse('tasks:task-detail-full', args=[task.pk])
        response = client.get(url)

        # Should show placeholder text
        assert b'Beschreibung hinzufügen' in response.content or b'Keine Beschreibung' in response.content


# Fixtures
@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def project(db, user):
    """Create a test project."""
    project = Project.objects.create(
        name='Test Project',
        slug='test-project',
        created_by=user
    )
    # Make user a member of the project
    project.user_members.add(user)
    return project
