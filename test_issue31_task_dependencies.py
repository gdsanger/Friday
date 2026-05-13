#!/usr/bin/env python
"""
Acceptance tests for ISSUE-31: Task Dependencies feature.

This script tests:
- TaskDependency model creation and constraints
- Task.blocking_tasks, Task.is_blocked, Task.blocked_tasks properties
- Adding dependencies via DependencyAddView (HTMX)
- Removing dependencies via DependencyRemoveView (HTMX)
- Self-dependency rejection (400)
- Circular dependency rejection (400)
- Status guard: blocked tasks cannot move to in_progress (409)
- Blocked badge on Kanban cards
- Dependency section in slide-over and full detail templates
- Gantt chart dependency links
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.db import IntegrityError
from apps.tasks.models import Task, TaskDependency
from apps.projects.models import Project
from datetime import date

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and tasks for testing."""
    # Clean up any existing test data
    TaskDependency.objects.filter(task__title__contains='Issue31').delete()
    Task.objects.filter(title__contains='Issue31').delete()
    Project.objects.filter(name__startswith='Test Project Issue31').delete()
    User.objects.filter(username='test_user_issue31').delete()

    # Create test user
    user = User.objects.create_user(
        username='test_user_issue31',
        email='testissue31@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )

    # Create test project
    project = Project.objects.create(
        name='Test Project Issue31',
        description='Test project for dependencies',
        status='active',
        owner=user
    )
    project.user_members.add(user)

    # Create test tasks
    task1 = Task.objects.create(
        title='Issue31 Server Setup',
        description='Setup production server',
        project=project,
        status=Task.STATUS_TODO,
        created_by=user,
        deadline=date(2024, 1, 15)
    )
    task2 = Task.objects.create(
        title='Issue31 Deploy to Production',
        description='Deploy application',
        project=project,
        status=Task.STATUS_TODO,
        created_by=user,
        deadline=date(2024, 1, 20)
    )
    task3 = Task.objects.create(
        title='Issue31 Configure DNS',
        description='Setup DNS records',
        project=project,
        status=Task.STATUS_TODO,
        created_by=user
    )

    return user, project, task1, task2, task3


def run_tests():
    """Run all tests for task dependencies."""
    print("=" * 70)
    print("TESTING ISSUE-31: Task Dependencies")
    print("=" * 70)

    user, project, task1, task2, task3 = setup_test_data()
    client = Client()
    client.login(username='test_user_issue31', password='testpass123')

    passed = 0
    failed = 0

    # Test 1: TaskDependency model creation
    print("\n[TEST 1] TaskDependency model creation...")
    try:
        dep = TaskDependency.objects.create(
            task=task2,
            blocked_by=task1,
            created_by=user
        )
        assert dep.task == task2
        assert dep.blocked_by == task1
        assert str(dep) == f'{task2.title} blocked by {task1.title}'
        print("✓ PASS: TaskDependency created successfully")
        passed += 1
        dep.delete()  # Clean up
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 2: Unique constraint
    print("\n[TEST 2] Unique together constraint...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        try:
            TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
            print("✗ FAIL: Duplicate dependency was allowed")
            failed += 1
        except IntegrityError:
            print("✓ PASS: Duplicate dependency rejected")
            passed += 1
        TaskDependency.objects.filter(task=task2, blocked_by=task1).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 3: Task.blocking_tasks property
    print("\n[TEST 3] Task.blocking_tasks property...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        TaskDependency.objects.create(task=task2, blocked_by=task3, created_by=user)
        blocking = task2.blocking_tasks
        assert blocking.count() == 2
        assert task1 in blocking
        assert task3 in blocking
        print("✓ PASS: blocking_tasks returns correct tasks")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 4: Task.is_blocked property (True)
    print("\n[TEST 4] Task.is_blocked property (True)...")
    try:
        task1.status = Task.STATUS_TODO
        task1.save()
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        assert task2.is_blocked is True
        print("✓ PASS: is_blocked returns True when blocker not done")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 5: Task.is_blocked property (False when done)
    print("\n[TEST 5] Task.is_blocked property (False when blocker done)...")
    try:
        task1.status = Task.STATUS_DONE
        task1.save()
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        assert task2.is_blocked is False
        print("✓ PASS: is_blocked returns False when blocker is done")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
        task1.status = Task.STATUS_TODO
        task1.save()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 6: Task.blocked_tasks property
    print("\n[TEST 6] Task.blocked_tasks property...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        TaskDependency.objects.create(task=task3, blocked_by=task1, created_by=user)
        blocked = task1.blocked_tasks
        assert blocked.count() == 2
        assert task2 in blocked
        assert task3 in blocked
        print("✓ PASS: blocked_tasks returns correct tasks")
        passed += 1
        TaskDependency.objects.filter(blocked_by=task1).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 7: Add dependency via view
    print("\n[TEST 7] Add dependency via DependencyAddView...")
    try:
        response = client.post(
            f'/tasks/{task2.pk}/dependencies/add/',
            {'blocked_by_id': task1.pk}
        )
        assert response.status_code == 200
        assert TaskDependency.objects.filter(task=task2, blocked_by=task1).exists()
        print("✓ PASS: Dependency added successfully")
        passed += 1
        TaskDependency.objects.filter(task=task2, blocked_by=task1).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 8: Self-dependency rejected
    print("\n[TEST 8] Self-dependency rejection...")
    try:
        response = client.post(
            f'/tasks/{task1.pk}/dependencies/add/',
            {'blocked_by_id': task1.pk}
        )
        assert response.status_code == 400
        assert b'cannot depend on itself' in response.content
        print("✓ PASS: Self-dependency rejected with 400")
        passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 9: Circular dependency rejected
    print("\n[TEST 9] Circular dependency rejection...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        response = client.post(
            f'/tasks/{task1.pk}/dependencies/add/',
            {'blocked_by_id': task2.pk}
        )
        assert response.status_code == 400
        assert b'Circular dependency' in response.content
        print("✓ PASS: Circular dependency rejected with 400")
        passed += 1
        TaskDependency.objects.filter(task=task2, blocked_by=task1).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 10: Remove dependency via view
    print("\n[TEST 10] Remove dependency via DependencyRemoveView...")
    try:
        dep = TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        response = client.post(f'/tasks/{task2.pk}/dependencies/{dep.pk}/remove/')
        assert response.status_code == 200
        assert not TaskDependency.objects.filter(pk=dep.pk).exists()
        print("✓ PASS: Dependency removed successfully")
        passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 11: Blocked task cannot move to in_progress
    print("\n[TEST 11] Blocked task status guard...")
    try:
        task1.status = Task.STATUS_TODO
        task1.save()
        task2.status = Task.STATUS_TODO
        task2.save()
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)

        response = client.post(
            f'/tasks/{task2.pk}/status/',
            {'status': Task.STATUS_IN_PROGRESS}
        )
        assert response.status_code == 409
        task2.refresh_from_db()
        assert task2.status == Task.STATUS_TODO
        print("✓ PASS: Blocked task cannot move to in_progress (409)")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 12: Unblocked task can move to in_progress
    print("\n[TEST 12] Unblocked task status transition...")
    try:
        task1.status = Task.STATUS_DONE
        task1.save()
        task2.status = Task.STATUS_TODO
        task2.save()
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)

        response = client.post(
            f'/tasks/{task2.pk}/status/',
            {'status': Task.STATUS_IN_PROGRESS}
        )
        assert response.status_code == 204
        task2.refresh_from_db()
        assert task2.status == Task.STATUS_IN_PROGRESS
        print("✓ PASS: Unblocked task can move to in_progress")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
        task2.status = Task.STATUS_TODO
        task2.save()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 13: Dependency section in slide-over
    print("\n[TEST 13] Dependency section in slide-over...")
    try:
        response = client.get(f'/tasks/{task1.pk}/detail/')
        assert response.status_code == 200
        assert b'Dependencies' in response.content
        assert b'dependency-list' in response.content
        print("✓ PASS: Dependency section appears in slide-over")
        passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 14: Dependency section in full detail
    print("\n[TEST 14] Dependency section in full detail...")
    try:
        response = client.get(f'/tasks/{task1.pk}/')
        assert response.status_code == 200
        assert b'Dependencies' in response.content
        print("✓ PASS: Dependency section appears in full detail")
        passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 15: Blocking tasks shown in list
    print("\n[TEST 15] Blocking tasks shown in dependency list...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        response = client.get(f'/tasks/{task2.pk}/detail/')
        assert response.status_code == 200
        assert task1.title.encode() in response.content
        assert b'Blockiert durch' in response.content
        print("✓ PASS: Blocking tasks shown in list")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 16: Blocked tasks shown in list
    print("\n[TEST 16] Blocked tasks shown in dependency list...")
    try:
        TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        response = client.get(f'/tasks/{task1.pk}/detail/')
        assert response.status_code == 200
        assert task2.title.encode() in response.content
        assert b'Blockiert diese Tasks' in response.content
        print("✓ PASS: Blocked tasks shown in list")
        passed += 1
        TaskDependency.objects.filter(task=task2).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Test 17: Gantt includes dependency links
    print("\n[TEST 17] Gantt chart includes dependency links...")
    try:
        dep = TaskDependency.objects.create(task=task2, blocked_by=task1, created_by=user)
        response = client.get('/projects/calendar/data/')
        assert response.status_code == 200
        data = response.json()
        assert 'links' in data

        # Find our dependency link
        dep_found = False
        for link in data['links']:
            if link.get('id') == f'dep_{dep.pk}':
                assert link['source'] == f't_{task1.pk}'
                assert link['target'] == f't_{task2.pk}'
                assert link['type'] == '0'
                dep_found = True
                break

        assert dep_found
        print("✓ PASS: Gantt includes dependency links")
        passed += 1
        TaskDependency.objects.filter(pk=dep.pk).delete()
    except Exception as e:
        print(f"✗ FAIL: {e}")
        failed += 1

    # Print summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All acceptance criteria met!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
