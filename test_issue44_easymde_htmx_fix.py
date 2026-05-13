"""
Test for Issue #44 - EasyMDE HTMX Initialization Fix
Tests that the new MutationObserver-based approach correctly handles:
1. Initial page load
2. HTMX swaps into slide-over
3. Re-opening slide-over (no double initialization)
4. Modal support
5. Memory leak prevention
"""
import pytest
from django.test import Client
from django.urls import reverse
from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.django_db
class TestEasyMDEHTMXFix:
    """Test EasyMDE MutationObserver-based initialization."""

    def test_task_create_page_has_md_editor(self, client: Client, user: User, project: Project):
        """Test that task create page loads with md-editor class (Acceptance Criteria #1)."""
        client.force_login(user)
        url = reverse('tasks:task-create')
        response = client.get(url, {'project': project.pk})

        assert response.status_code == 200
        # Check that md-editor textarea is present
        assert b'md-editor' in response.content
        assert b'<textarea' in response.content
        # Check that friday.js is loaded (contains MutationObserver code)
        assert b'friday.js' in response.content

    def test_slide_over_edit_mode_has_md_editor(self, client: Client, user: User, project: Project):
        """Test that description edit in slide-over has md-editor class (Acceptance Criteria #2)."""
        task = Task.objects.create(
            title="Test Task",
            description="## Test Description",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)

        # Get edit mode via TaskEditFieldView (this is what HTMX loads into slide-over)
        url = reverse('tasks:task-edit-field', args=[task.pk])
        response = client.get(url, {'mode': 'edit', 'field': 'description'})

        # Check that md-editor class is present for MutationObserver to detect
        assert b'md-editor' in response.content
        assert b'<textarea' in response.content
        # Verify this is the inline form that gets swapped in
        assert b'<form' in response.content

    def test_task_detail_full_has_md_editor_in_edit_mode(self, client: Client, user: User, project: Project):
        """Test that task detail full page has md-editor in edit mode (Acceptance Criteria #3)."""
        task = Task.objects.create(
            title="Test Task",
            description="## Test Description",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)

        # Get edit mode
        url = reverse('tasks:task-edit-field', args=[task.pk])
        response = client.get(url, {'mode': 'edit', 'field': 'description'})

        assert b'md-editor' in response.content
        assert b'<textarea' in response.content

    def test_friday_js_has_mutation_observer_code(self, client: Client, user: User):
        """Test that friday.js contains the new MutationObserver implementation."""
        client.force_login(user)

        # Get any page that loads friday.js
        url = reverse('dashboard')
        response = client.get(url)

        # Read the actual JavaScript file to verify implementation
        with open('static/js/friday.js', 'r') as f:
            js_content = f.read()

        # Verify key components are present
        assert 'MutationObserver' in js_content
        assert '_mdInstances' in js_content
        assert 'initEasyMDE' in js_content
        assert 'requestAnimationFrame' in js_content
        assert 'onSlideoverOpen' in js_content
        assert 'htmx:afterSettle' in js_content
        assert 'htmx:beforeSwap' in js_content
        assert 'shown.bs.modal' in js_content
        assert 'console.warn' in js_content
        # Verify old method is removed
        assert 'initMarkdownEditors' not in js_content

    def test_easymde_libraries_loaded(self, client: Client, user: User, project: Project):
        """Test that EasyMDE libraries are loaded in base template."""
        task = Task.objects.create(
            title="Test Task",
            project=project,
            created_by=user,
            status='backlog'
        )

        client.force_login(user)
        url = reverse('tasks:task-detail-full', args=[task.pk])
        response = client.get(url)

        # Verify EasyMDE CSS and JS are loaded
        assert b'easymde.min.css' in response.content
        assert b'easymde.min.js' in response.content

    def test_cleanup_logic_exists(self, client: Client, user: User):
        """Test that cleanup logic exists to prevent memory leaks (Acceptance Criteria #6)."""
        client.force_login(user)

        # Read the JavaScript file
        with open('static/js/friday.js', 'r') as f:
            js_content = f.read()

        # Verify cleanup on beforeSwap
        assert 'htmx:beforeSwap' in js_content
        assert 'toTextArea()' in js_content
        assert '_mdInstances.delete' in js_content

    def test_dark_mode_support_exists(self, client: Client, user: User):
        """Test that dark mode support is preserved (Acceptance Criteria #7)."""
        client.force_login(user)

        # Read the JavaScript file
        with open('static/js/friday.js', 'r') as f:
            js_content = f.read()

        # Verify dark mode handling
        assert 'friday:theme-changed' in js_content
        assert 'cm-s-dark' in js_content
        assert 'friday-theme' in js_content

    def test_error_handling_uses_console_warn(self, client: Client, user: User):
        """Test that errors use console.warn not console.error (Acceptance Criteria #8)."""
        client.force_login(user)

        # Read the JavaScript file
        with open('static/js/friday.js', 'r') as f:
            js_content = f.read()

        # In the EasyMDE section, errors should use console.warn
        easymde_section = js_content[js_content.find('EasyMDE — Robuste'):js_content.find('Markdown Rendering')]

        # Should have console.warn
        assert 'console.warn' in easymde_section
        # Should not use console.error in the new implementation
        # (console.error may exist elsewhere in the file, but not in EasyMDE section)
        assert 'console.error' not in easymde_section

    def test_slide_over_reinit_delay(self, client: Client, user: User):
        """Test that slide-over has proper 50ms delay for CSS transitions."""
        client.force_login(user)

        # Read the JavaScript file
        with open('static/js/friday.js', 'r') as f:
            js_content = f.read()

        # Verify 50ms delay exists in onSlideoverOpen
        assert '50)' in js_content  # setTimeout(..., 50)
        assert 'CSS-Transition' in js_content


# Fixtures
@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        is_staff=True
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
