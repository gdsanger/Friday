#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-38: Requester-Feld auf Task.

This script tests:
- Task.requester ForeignKey exists and is nullable
- Migration runs successfully
- Task.effective_requester returns requester or created_by
- Requester field appears in task slide-over and full detail views
- Requester is inline editable via TaskEditFieldView
- Requester field appears in task creation form
- TaskEditFieldView supports field=requester
- Kanban card shows requester when different from assignee
- Mail dispatcher handles 'requester' recipient type
- RECIPIENT_CHOICES contains 'requester'
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.projects.models import Project
from apps.tasks.models import Task
from apps.mail.models import MailHook
from apps.mail.dispatcher import _resolve_recipients

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks."""
    # Clean up any existing test data first
    Task.objects.filter(title__contains='Issue38').delete()
    Project.objects.filter(name__startswith='Test Project Issue38').delete()
    User.objects.filter(username__startswith='test_').filter(username__contains='issue38').delete()

    # Create test users
    creator_user = User.objects.create_user(
        username='test_creator_issue38',
        email='creator38@test.com',
        password='testpass123',
        display_name='Test Creator Issue38',
        notify_email=True
    )

    requester_user = User.objects.create_user(
        username='test_requester_issue38',
        email='requester38@test.com',
        password='testpass123',
        display_name='Test Requester Issue38',
        notify_email=True
    )

    assignee_user = User.objects.create_user(
        username='test_assignee_issue38',
        email='assignee38@test.com',
        password='testpass123',
        display_name='Test Assignee Issue38',
        notify_email=True
    )

    other_user = User.objects.create_user(
        username='test_other_issue38',
        email='other38@test.com',
        password='testpass123',
        display_name='Test Other Issue38',
        notify_email=True
    )

    # Create test project
    project = Project.objects.create(
        name='Test Project Issue38',
        description='Test project for issue 38',
        status='active',
        color='#2980b9',
        owner=creator_user
    )
    project.user_members.add(creator_user, requester_user, assignee_user, other_user)

    return {
        'creator_user': creator_user,
        'requester_user': requester_user,
        'assignee_user': assignee_user,
        'other_user': other_user,
        'project': project,
    }


def test_requester_field_exists():
    """Test that Task.requester field exists and is nullable."""
    print("Testing Task.requester field existence...")

    data = setup_test_data()

    # Create task without requester (should be allowed)
    task1 = Task.objects.create(
        title='Issue38 Task 1 - No Requester',
        description='Task without requester',
        project=data['project'],
        status=Task.STATUS_BACKLOG,
        created_by=data['creator_user']
    )

    assert task1.requester is None, "Task without requester should have None"
    print("✓ Task can be created without requester")

    # Create task with requester
    task2 = Task.objects.create(
        title='Issue38 Task 2 - With Requester',
        description='Task with requester',
        project=data['project'],
        status=Task.STATUS_BACKLOG,
        created_by=data['creator_user'],
        requester=data['requester_user']
    )

    assert task2.requester == data['requester_user'], "Task requester should be set"
    assert task2.created_by == data['creator_user'], "Task creator should be different from requester"
    print("✓ Task can be created with requester")
    print("✓ Task.requester field exists and is nullable")


def test_effective_requester_property():
    """Test that effective_requester returns requester or falls back to created_by."""
    print("\nTesting Task.effective_requester property...")

    data = setup_test_data()

    # Task with requester set
    task_with_requester = Task.objects.create(
        title='Issue38 Task - With Requester',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['requester_user']
    )

    assert task_with_requester.effective_requester == data['requester_user'], \
        "effective_requester should return requester when set"
    print("✓ effective_requester returns requester when set")

    # Task without requester
    task_without_requester = Task.objects.create(
        title='Issue38 Task - No Requester',
        project=data['project'],
        created_by=data['creator_user']
    )

    assert task_without_requester.effective_requester == data['creator_user'], \
        "effective_requester should fall back to created_by"
    print("✓ effective_requester falls back to created_by when requester is None")


def test_requester_in_task_detail_views():
    """Test that requester field appears in slide-over and full detail views."""
    print("\nTesting requester field in task detail views...")

    data = setup_test_data()

    task = Task.objects.create(
        title='Issue38 Task - For View Test',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['requester_user']
    )

    client = Client()
    client.force_login(data['creator_user'])

    # Test slide-over view
    response = client.get(reverse('tasks:task-detail', args=[task.pk]))
    assert response.status_code == 200, "Slide-over view should be accessible"
    content = response.content.decode('utf-8')
    assert 'Angefordert von' in content, "Slide-over should contain requester label"
    assert data['requester_user'].full_name in content, "Slide-over should show requester name"
    print("✓ Requester field appears in slide-over view")

    # Test full detail view
    response = client.get(reverse('tasks:task-detail-full', args=[task.pk]))
    assert response.status_code == 200, "Full detail view should be accessible"
    content = response.content.decode('utf-8')
    assert 'Angefordert von' in content, "Full detail should contain requester label"
    assert data['requester_user'].full_name in content, "Full detail should show requester name"
    print("✓ Requester field appears in full detail view")


def test_requester_inline_editing():
    """Test that requester is inline editable via TaskEditFieldView."""
    print("\nTesting requester inline editing...")

    data = setup_test_data()

    task = Task.objects.create(
        title='Issue38 Task - For Edit Test',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['requester_user']
    )

    client = Client()
    client.force_login(data['creator_user'])

    # Test GET edit mode
    response = client.get(
        reverse('tasks:task-edit-field', args=[task.pk]),
        {'mode': 'edit', 'field': 'requester'}
    )
    assert response.status_code == 200, "GET edit mode should work"
    content = response.content.decode('utf-8')
    assert 'select' in content.lower(), "Edit mode should show dropdown"
    assert data['other_user'].full_name in content, "Dropdown should include project members"
    print("✓ GET edit mode returns requester dropdown")

    # Test POST to change requester
    response = client.post(
        reverse('tasks:task-edit-field', args=[task.pk]),
        {'field': 'requester', 'value': str(data['other_user'].pk)}
    )
    assert response.status_code == 200, "POST should succeed"
    task.refresh_from_db()
    assert task.requester == data['other_user'], "Requester should be updated"
    print("✓ POST updates requester successfully")

    # Test POST to clear requester
    response = client.post(
        reverse('tasks:task-edit-field', args=[task.pk]),
        {'field': 'requester', 'value': ''}
    )
    assert response.status_code == 200, "POST should succeed"
    task.refresh_from_db()
    assert task.requester is None, "Requester should be cleared"
    print("✓ POST can clear requester")


def test_requester_in_create_form():
    """Test that requester field appears in task creation form."""
    print("\nTesting requester in creation form...")

    data = setup_test_data()

    client = Client()
    client.force_login(data['creator_user'])

    # Test slide-over creation form
    response = client.get(
        reverse('tasks:task-create'),
        {'slide_over': '1', 'project_id': data['project'].pk},
        HTTP_HX_REQUEST='true'
    )
    assert response.status_code == 200, "Slide-over form should be accessible"
    content = response.content.decode('utf-8')
    assert 'Angefordert von' in content, "Form should have requester label"
    assert 'name="requester"' in content, "Form should have requester field"
    print("✓ Requester field appears in creation form")

    # Test creating task with requester
    response = client.post(
        reverse('tasks:task-create'),
        {
            'project': data['project'].pk,
            'title': 'Issue38 Task - Created with Requester',
            'description': 'Test task',
            'status': Task.STATUS_BACKLOG,
            'priority': Task.PRIORITY_MEDIUM,
            'requester': data['requester_user'].pk,
        },
        HTTP_HX_REQUEST='true'
    )
    assert response.status_code in [200, 302], "Task creation should succeed"

    task = Task.objects.filter(title='Issue38 Task - Created with Requester').first()
    assert task is not None, "Task should be created"
    assert task.requester == data['requester_user'], "Requester should be set from form"
    assert task.created_by == data['creator_user'], "Creator should be the logged-in user"
    print("✓ Task can be created with requester from form")


def test_requester_on_kanban_card():
    """Test that Kanban card shows requester when different from assignee."""
    print("\nTesting requester on Kanban card...")

    data = setup_test_data()

    # Task where requester != assignee
    task1 = Task.objects.create(
        title='Issue38 Task - Different Requester',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['requester_user'],
        assigned_to_user=data['assignee_user']
    )

    # Task where requester == assignee
    task2 = Task.objects.create(
        title='Issue38 Task - Same Requester',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['assignee_user'],
        assigned_to_user=data['assignee_user']
    )

    # Task without requester
    task3 = Task.objects.create(
        title='Issue38 Task - No Requester',
        project=data['project'],
        created_by=data['creator_user'],
        assigned_to_user=data['assignee_user']
    )

    # Check that card template renders correctly
    from django.template.loader import render_to_string

    card_html_1 = render_to_string('tasks/partials/card.html', {'task': task1})
    assert 'bi-person-raised-hand' in card_html_1, "Card should show requester icon when different from assignee"
    assert data['requester_user'].full_name in card_html_1, "Card should show requester name"
    print("✓ Kanban card shows requester when different from assignee")

    card_html_2 = render_to_string('tasks/partials/card.html', {'task': task2})
    assert 'bi-person-raised-hand' not in card_html_2, "Card should NOT show requester when same as assignee"
    print("✓ Kanban card hides requester when same as assignee")

    card_html_3 = render_to_string('tasks/partials/card.html', {'task': task3})
    assert 'bi-person-raised-hand' not in card_html_3, "Card should NOT show requester when not set"
    print("✓ Kanban card handles missing requester")


def test_mail_recipient_requester():
    """Test that mail dispatcher handles 'requester' recipient type."""
    print("\nTesting mail dispatcher requester recipient...")

    data = setup_test_data()

    # Create a mail hook with requester recipient
    hook, _ = MailHook.objects.get_or_create(
        event='task_created',
        defaults={
            'is_active': True,
            'recipients': ['requester'],
            'template_name': 'task_created',
            'subject_template': 'New task: {task_title}',
        }
    )
    hook.recipients = ['requester']
    hook.save()

    # Task with requester
    task = Task.objects.create(
        title='Issue38 Task - For Mail Test',
        project=data['project'],
        created_by=data['creator_user'],
        requester=data['requester_user']
    )

    recipients = _resolve_recipients(hook, task)
    assert data['requester_user'].email in recipients, "Requester should be in recipient list"
    print("✓ Mail dispatcher resolves 'requester' recipient type")

    # Task without requester (should use created_by via effective_requester)
    task2 = Task.objects.create(
        title='Issue38 Task - No Requester Mail Test',
        project=data['project'],
        created_by=data['creator_user']
    )

    recipients2 = _resolve_recipients(hook, task2)
    assert data['creator_user'].email in recipients2, "effective_requester should fall back to creator"
    print("✓ Mail dispatcher uses effective_requester (falls back to creator)")


def test_recipient_choices_contains_requester():
    """Test that RECIPIENT_CHOICES contains 'requester'."""
    print("\nTesting RECIPIENT_CHOICES...")

    from apps.mail.models import MailHook

    recipient_types = [choice[0] for choice in MailHook.RECIPIENT_CHOICES]
    assert 'requester' in recipient_types, "RECIPIENT_CHOICES should contain 'requester'"
    assert MailHook.RECIPIENT_REQUESTER == 'requester', "RECIPIENT_REQUESTER constant should exist"
    print("✓ RECIPIENT_CHOICES contains 'requester'")
    print("✓ RECIPIENT_REQUESTER constant exists")


def run_all_tests():
    """Run all acceptance tests."""
    print("=" * 70)
    print("ISSUE-38 Acceptance Tests: Requester Field on Task")
    print("=" * 70)

    try:
        test_requester_field_exists()
        test_effective_requester_property()
        test_requester_in_task_detail_views()
        test_requester_inline_editing()
        test_requester_in_create_form()
        test_requester_on_kanban_card()
        test_mail_recipient_requester()
        test_recipient_choices_contains_requester()

        print("\n" + "=" * 70)
        print("✓ ALL ACCEPTANCE TESTS PASSED!")
        print("=" * 70)
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
