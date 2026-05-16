#!/usr/bin/env python
"""
Acceptance tests for ISSUE-61: Task Move to Another Project.

This script tests:
- TaskMoveProjectFormView requires manager role or staff
- TaskMoveProjectFormView shows accessible projects (excluding current & archived)
- TaskMoveProjectView requires manager role on source project
- TaskMoveProjectView requires membership on target project
- TaskMoveProjectView moves task to new project
- TaskMoveProjectView moves all subtasks to new project
- TaskMoveProjectView inherits client from new project if task has no client
- TaskMoveProjectView resolves dependencies to tasks in old project
- TaskMoved event triggers UI updates
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from apps.tasks.models import Task, TaskDependency
from apps.projects.models import Project, ProjectUserMembership
from apps.core.models import Client as ClientModel

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks for testing."""
    # Clean up any existing test data
    Task.objects.filter(title__contains='Issue61').delete()
    Project.objects.filter(name__startswith='Test Project Issue61').delete()
    User.objects.filter(username__startswith='test_user_issue61').delete()
    ClientModel.objects.filter(name__contains='Issue61').delete()

    # Create users
    manager = User.objects.create_user(
        username='test_user_issue61_manager',
        email='manager61@test.com',
        password='testpass123',
        display_name='Manager User',
        is_active=True,
    )

    contributor = User.objects.create_user(
        username='test_user_issue61_contributor',
        email='contributor61@test.com',
        password='testpass123',
        display_name='Contributor User',
        is_active=True,
    )

    other_user = User.objects.create_user(
        username='test_user_issue61_other',
        email='other61@test.com',
        password='testpass123',
        display_name='Other User',
        is_active=True,
    )

    # Create clients
    client1 = ClientModel.objects.create(
        name='Client Issue61-A',
        short_name='CL61A',
        is_active=True,
    )

    client2 = ClientModel.objects.create(
        name='Client Issue61-B',
        short_name='CL61B',
        is_active=True,
    )

    # Create source project
    project_source = Project.objects.create(
        name='Test Project Issue61 Source',
        status='active',
        client=client1,
    )
    ProjectUserMembership.objects.create(
        project=project_source,
        user=manager,
        role='manager',
    )
    ProjectUserMembership.objects.create(
        project=project_source,
        user=contributor,
        role='contributor',
    )

    # Create target project
    project_target = Project.objects.create(
        name='Test Project Issue61 Target',
        status='active',
        client=client2,
    )
    ProjectUserMembership.objects.create(
        project=project_target,
        user=manager,
        role='manager',
    )
    ProjectUserMembership.objects.create(
        project=project_target,
        user=contributor,
        role='contributor',
    )

    # Create archived project
    project_archived = Project.objects.create(
        name='Test Project Issue61 Archived',
        status='archived',
    )
    ProjectUserMembership.objects.create(
        project=project_archived,
        user=manager,
        role='manager',
    )

    # Create project without access
    project_no_access = Project.objects.create(
        name='Test Project Issue61 No Access',
        status='active',
    )
    ProjectUserMembership.objects.create(
        project=project_no_access,
        user=other_user,
        role='manager',
    )

    # Create task with subtasks
    task = Task.objects.create(
        title='Main Task Issue61',
        description='Test task for move',
        project=project_source,
        status=Task.STATUS_TODO,
        created_by=manager,
        requester=manager,
    )

    subtask1 = Task.objects.create(
        title='Subtask 1 Issue61',
        project=project_source,
        parent_task=task,
        status=Task.STATUS_TODO,
        created_by=manager,
    )

    subtask2 = Task.objects.create(
        title='Subtask 2 Issue61',
        project=project_source,
        parent_task=task,
        status=Task.STATUS_TODO,
        created_by=manager,
    )

    # Create dependency task in same project
    dep_task = Task.objects.create(
        title='Dependency Task Issue61',
        project=project_source,
        status=Task.STATUS_TODO,
        created_by=manager,
    )

    TaskDependency.objects.create(
        task=task,
        blocked_by=dep_task,
        created_by=manager,
    )

    return {
        'manager': manager,
        'contributor': contributor,
        'other_user': other_user,
        'project_source': project_source,
        'project_target': project_target,
        'project_archived': project_archived,
        'project_no_access': project_no_access,
        'task': task,
        'subtask1': subtask1,
        'subtask2': subtask2,
        'dep_task': dep_task,
        'client1': client1,
        'client2': client2,
    }


def test_move_form_requires_manager_role():
    """Test that move form requires manager role or staff."""
    print("\n1. Testing move form permission (manager/staff only)...")
    data = setup_test_data()
    client = Client()

    # Contributor should not have access
    client.force_login(data['contributor'])
    response = client.get(f"/tasks/{data['task'].pk}/move-project/form/")
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print("   ✓ Contributor correctly denied access")

    # Manager should have access
    client.force_login(data['manager'])
    response = client.get(f"/tasks/{data['task'].pk}/move-project/form/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("   ✓ Manager has access to move form")


def test_move_form_shows_accessible_projects():
    """Test that form shows only accessible, non-archived projects excluding current."""
    print("\n2. Testing project list in form...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.get(f"/tasks/{data['task'].pk}/move-project/form/")
    content = response.content.decode()

    # Should show target project
    assert data['project_target'].name in content, "Target project should be in list"
    print(f"   ✓ Target project '{data['project_target'].name}' shown")

    # Should NOT show current project
    assert data['project_source'].name not in content or 'Aktuelles Projekt' in content, \
        "Source project should not be in dropdown"
    print(f"   ✓ Source project not in dropdown")

    # Should NOT show archived project
    assert data['project_archived'].name not in content, "Archived project should not be in list"
    print(f"   ✓ Archived project not shown")

    # Should NOT show project without access
    assert data['project_no_access'].name not in content, "No-access project should not be in list"
    print(f"   ✓ No-access project not shown")


def test_move_task_permissions():
    """Test permission checks for moving task."""
    print("\n3. Testing move task permissions...")
    data = setup_test_data()
    client = Client()

    # Contributor should not be able to move
    client.force_login(data['contributor'])
    response = client.post(
        f"/tasks/{data['task'].pk}/move-project/",
        {'project_id': data['project_target'].pk}
    )
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print("   ✓ Contributor correctly denied move action")

    # Manager should be able to move
    client.force_login(data['manager'])
    response = client.post(
        f"/tasks/{data['task'].pk}/move-project/",
        {'project_id': data['project_target'].pk}
    )
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    assert response['HX-Trigger'] == 'taskMoved', "Should have taskMoved trigger"
    print("   ✓ Manager successfully moved task")


def test_move_task_and_subtasks():
    """Test that task and subtasks are moved together."""
    print("\n4. Testing task and subtask move...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    task_id = data['task'].pk
    subtask1_id = data['subtask1'].pk
    subtask2_id = data['subtask2'].pk
    target_project_id = data['project_target'].pk

    response = client.post(
        f"/tasks/{task_id}/move-project/",
        {'project_id': target_project_id}
    )
    assert response.status_code == 204

    # Verify task moved
    task = Task.objects.get(pk=task_id)
    assert task.project_id == target_project_id, "Task should be in target project"
    print(f"   ✓ Task moved to {data['project_target'].name}")

    # Verify subtasks moved
    subtask1 = Task.objects.get(pk=subtask1_id)
    subtask2 = Task.objects.get(pk=subtask2_id)
    assert subtask1.project_id == target_project_id, "Subtask1 should be in target project"
    assert subtask2.project_id == target_project_id, "Subtask2 should be in target project"
    print("   ✓ All subtasks moved with parent task")


def test_client_inheritance():
    """Test that task inherits client from new project if not set."""
    print("\n5. Testing client inheritance...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    task_id = data['task'].pk
    target_project_id = data['project_target'].pk

    # Task initially has no direct client
    task = Task.objects.get(pk=task_id)
    assert task.client is None, "Task should start with no direct client"

    response = client.post(
        f"/tasks/{task_id}/move-project/",
        {'project_id': target_project_id}
    )
    assert response.status_code == 204

    # Verify client inherited
    task = Task.objects.get(pk=task_id)
    assert task.client == data['client2'], "Task should inherit client from target project"
    print(f"   ✓ Task inherited client '{data['client2'].short_name}' from target project")


def test_dependency_resolution():
    """Test that dependencies to old project tasks are resolved."""
    print("\n6. Testing dependency resolution...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    task_id = data['task'].pk
    dep_task_id = data['dep_task'].pk
    target_project_id = data['project_target'].pk

    # Verify dependency exists
    assert TaskDependency.objects.filter(
        task_id=task_id,
        blocked_by_id=dep_task_id
    ).exists(), "Dependency should exist before move"
    print("   ✓ Dependency exists before move")

    response = client.post(
        f"/tasks/{task_id}/move-project/",
        {'project_id': target_project_id}
    )
    assert response.status_code == 204

    # Verify dependency removed
    assert not TaskDependency.objects.filter(
        task_id=task_id,
        blocked_by_id=dep_task_id
    ).exists(), "Dependency should be removed after move"
    print("   ✓ Dependency to old project task resolved")


def test_missing_project_id():
    """Test that missing project_id returns 400."""
    print("\n7. Testing missing project_id validation...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.post(
        f"/tasks/{data['task'].pk}/move-project/",
        {}  # No project_id
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    print("   ✓ Missing project_id correctly returns 400")


def test_no_access_to_target_project():
    """Test that user needs membership in target project."""
    print("\n8. Testing target project membership requirement...")
    data = setup_test_data()
    client = Client()
    client.force_login(data['manager'])

    response = client.post(
        f"/tasks/{data['task'].pk}/move-project/",
        {'project_id': data['project_no_access'].pk}
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    print("   ✓ Non-member correctly denied access to target project")


def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("ISSUE-61: Task Move to Another Project - Acceptance Tests")
    print("=" * 60)

    try:
        test_move_form_requires_manager_role()
        test_move_form_shows_accessible_projects()
        test_move_task_permissions()
        test_move_task_and_subtasks()
        test_client_inheritance()
        test_dependency_resolution()
        test_missing_project_id()
        test_no_access_to_target_project()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
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
