#!/usr/bin/env python
"""
Test script to verify all acceptance criteria for ISSUE-15.

This script tests:
- Task title and description inline editing
- Full-page detail view exists
- Attachments upload, list, and delete
- Time entry logging and deletion
"""

import os
import sys
import django

# Setup Django with SQLite for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ['DATABASE_URL'] = 'sqlite:///test_db.sqlite3'
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.tasks.models import Task, Attachment, TimeEntry
from apps.projects.models import Project, ProjectUserMembership
from apps.core.models import Organisation
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


def setup_test_data():
    """Create test user, project, and task."""
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()

    # Create test project
    project, created = Project.objects.get_or_create(
        name='Test Project',
        defaults={
            'description': 'Test project for ISSUE-15',
            'owner': user,
        }
    )

    # Add user as project member
    ProjectUserMembership.objects.get_or_create(
        project=project,
        user=user,
        defaults={'role': 'manager'}
    )

    # Create test task
    task, created = Task.objects.get_or_create(
        title='Test Task for ISSUE-15',
        project=project,
        defaults={
            'description': 'Initial description',
            'status': Task.STATUS_TODO,
            'created_by': user,
        }
    )

    return user, project, task


def test_task_edit_field_view_exists():
    """Test TaskEditFieldView is accessible."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    # Test GET request for edit mode
    url = reverse('tasks:task-edit-field', args=[task.pk])
    response = client.get(url, {'mode': 'edit', 'field': 'title'})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'<input' in response.content, "Edit form not found in response"
    print("✓ TaskEditFieldView GET (edit mode) works")

    # Test GET request for view mode
    response = client.get(url, {'mode': 'view', 'field': 'title'})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ TaskEditFieldView GET (view mode) works")

    # Test POST request to update title
    response = client.post(url, {
        'field': 'title',
        'value': 'Updated Title',
    })
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    task.refresh_from_db()
    assert task.title == 'Updated Title', f"Title not updated: {task.title}"
    print("✓ TaskEditFieldView POST (title update) works")

    # Test POST request to update description
    response = client.post(url, {
        'field': 'description',
        'value': 'Updated description text',
    })
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    task.refresh_from_db()
    assert task.description == 'Updated description text', f"Description not updated: {task.description}"
    print("✓ TaskEditFieldView POST (description update) works")

    # Test empty title validation
    response = client.post(url, {
        'field': 'title',
        'value': '',
    })
    assert response.status_code == 400, f"Expected 400 for empty title, got {response.status_code}"
    print("✓ Empty title validation works")


def test_task_detail_full_view_exists():
    """Test TaskDetailFullView is accessible."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail-full', args=[task.pk])
    response = client.get(url)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'breadcrumb' in response.content, "Breadcrumb not found in full detail view"
    assert task.title.encode() in response.content, "Task title not found in response"
    print("✓ TaskDetailFullView works")
    print("✓ Breadcrumb is present in full detail view")


def test_field_title_partial_exists():
    """Test field_title.html partial template exists."""
    import os
    template_path = 'templates/tasks/partials/field_title.html'
    assert os.path.exists(template_path), f"Template {template_path} does not exist"
    print("✓ field_title.html partial exists")


def test_field_description_partial_exists():
    """Test field_description.html partial template exists."""
    import os
    template_path = 'templates/tasks/partials/field_description.html'
    assert os.path.exists(template_path), f"Template {template_path} does not exist"
    print("✓ field_description.html partial exists")


def test_attachment_upload_view():
    """Test AttachmentUploadView works."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create a test file
    test_file = SimpleUploadedFile(
        "test_document.txt",
        b"This is test file content",
        content_type="text/plain"
    )

    url = reverse('tasks:attachment-upload', args=[task.pk])
    response = client.post(url, {'file': test_file})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify attachment was created
    assert task.attachments.count() > 0, "No attachments were created"
    attachment = task.attachments.first()
    assert attachment.filename == "test_document.txt", f"Filename mismatch: {attachment.filename}"
    assert attachment.uploaded_by == user, "Uploader mismatch"
    print("✓ AttachmentUploadView works")
    print("✓ Attachment record created correctly")


def test_attachment_download_view():
    """Test AttachmentDownloadView works."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create an attachment first
    test_file = SimpleUploadedFile(
        "download_test.txt",
        b"Download test content",
        content_type="text/plain"
    )
    attachment = Attachment.objects.create(
        task=task,
        uploaded_by=user,
        file=test_file,
        filename="download_test.txt",
        size_bytes=len(b"Download test content")
    )

    url = reverse('tasks:attachment-download', args=[attachment.pk])
    response = client.get(url)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.headers.get('Content-Disposition'), "Content-Disposition header missing"
    print("✓ AttachmentDownloadView works")


def test_attachment_delete_view():
    """Test AttachmentDeleteView works."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create an attachment
    test_file = SimpleUploadedFile(
        "delete_test.txt",
        b"Delete test content",
        content_type="text/plain"
    )
    attachment = Attachment.objects.create(
        task=task,
        uploaded_by=user,
        file=test_file,
        filename="delete_test.txt",
        size_bytes=len(b"Delete test content")
    )

    attachment_pk = attachment.pk
    url = reverse('tasks:attachment-delete', args=[attachment_pk])
    response = client.post(url)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify attachment was deleted
    assert not Attachment.objects.filter(pk=attachment_pk).exists(), "Attachment was not deleted"
    print("✓ AttachmentDeleteView works")
    print("✓ Attachment deleted from database")


def test_time_entry_log_view():
    """Test TimeEntryLogView works."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    initial_count = task.time_entries.count()

    url = reverse('tasks:time-log', args=[task.pk])
    response = client.post(url, {
        'duration_m': 30,
        'note': 'Test time entry'
    })
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify time entry was created
    assert task.time_entries.count() == initial_count + 1, "Time entry was not created"
    entry = task.time_entries.first()
    assert entry.duration_m == 30, f"Duration mismatch: {entry.duration_m}"
    assert entry.note == 'Test time entry', f"Note mismatch: {entry.note}"
    assert entry.user == user, "User mismatch"
    print("✓ TimeEntryLogView works")
    print("✓ Time entry created correctly")


def test_time_entry_delete_view():
    """Test TimeEntryDeleteView works."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    # Create a time entry
    from django.utils import timezone
    entry = TimeEntry.objects.create(
        task=task,
        user=user,
        started_at=timezone.now(),
        duration_m=45,
        note='Test entry to delete'
    )

    entry_pk = entry.pk
    url = reverse('tasks:time-delete', args=[entry_pk])
    response = client.post(url)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify time entry was deleted
    assert not TimeEntry.objects.filter(pk=entry_pk).exists(), "Time entry was not deleted"
    print("✓ TimeEntryDeleteView works")
    print("✓ Time entry deleted from database")


def test_template_tag_file_icon():
    """Test file_icon template tag."""
    from apps.core.templatetags.friday_tags import file_icon

    assert file_icon('document.pdf') == 'bi-file-earmark-pdf'
    assert file_icon('spreadsheet.xlsx') == 'bi-file-earmark-excel'
    assert file_icon('image.png') == 'bi-file-earmark-image'
    assert file_icon('code.py') == 'bi-file-earmark-code'
    assert file_icon('unknown.xyz') == 'bi-file-earmark'
    print("✓ file_icon template tag works")


def test_attachment_list_partial_exists():
    """Test attachment_list.html partial template exists."""
    import os
    template_path = 'templates/tasks/partials/attachment_list.html'
    assert os.path.exists(template_path), f"Template {template_path} does not exist"
    print("✓ attachment_list.html partial exists")


def test_time_entry_list_partial_exists():
    """Test time_entry_list.html partial template exists."""
    import os
    template_path = 'templates/tasks/partials/time_entry_list.html'
    assert os.path.exists(template_path), f"Template {template_path} does not exist"
    print("✓ time_entry_list.html partial exists")


def test_detail_full_template_exists():
    """Test detail_full.html template exists."""
    import os
    template_path = 'templates/tasks/detail_full.html'
    assert os.path.exists(template_path), f"Template {template_path} does not exist"
    print("✓ detail_full.html template exists")


def test_slide_over_has_fullscreen_button():
    """Test slide_over.html has fullscreen button."""
    user, project, task = setup_test_data()
    client = Client()
    client.force_login(user)

    url = reverse('tasks:task-detail', args=[task.pk])
    response = client.get(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'bi-arrows-fullscreen' in response.content, "Fullscreen button not found in slide-over"
    print("✓ Slide-over has fullscreen button")


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("ISSUE-15 Acceptance Criteria Tests")
    print("="*60 + "\n")

    tests = [
        ("Task Edit Field View", test_task_edit_field_view_exists),
        ("Task Detail Full View", test_task_detail_full_view_exists),
        ("Field Title Partial", test_field_title_partial_exists),
        ("Field Description Partial", test_field_description_partial_exists),
        ("Attachment Upload", test_attachment_upload_view),
        ("Attachment Download", test_attachment_download_view),
        ("Attachment Delete", test_attachment_delete_view),
        ("Time Entry Log", test_time_entry_log_view),
        ("Time Entry Delete", test_time_entry_delete_view),
        ("Template Tag file_icon", test_template_tag_file_icon),
        ("Attachment List Partial", test_attachment_list_partial_exists),
        ("Time Entry List Partial", test_time_entry_list_partial_exists),
        ("Detail Full Template", test_detail_full_template_exists),
        ("Slide-over Fullscreen Button", test_slide_over_has_fullscreen_button),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}:")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
