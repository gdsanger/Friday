"""
Integration tests for Gantt task duration from story points (ISSUE-39).
"""
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.core.models import Client as ClientModel
import json


class GanttTaskDurationTestCase(TestCase):
    """Test Gantt task duration calculation from story points."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client_obj = ClientModel.objects.create(
            name='Test Client',
            slug='test-client',
            short_name='TC'
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
            start_date=date(2026, 6, 1),
            due_date=date(2026, 6, 30),
            color='#3b82f6'
        )
        self.project.user_members.add(self.user)

    def test_task_with_story_points_renders_as_bar(self):
        """Tasks with story points should render as bars with start/end dates."""
        task = Task.objects.create(
            title='Task with SP',
            project=self.project,
            deadline=date(2026, 6, 20),  # Friday
            story_points=16,  # 2 working days
            status='todo',
            priority=2
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Find the task in the response
        task_data = None
        for item in data['data']:
            if item.get('task_id') == task.pk:
                task_data = item
                break

        self.assertIsNotNone(task_data, "Task not found in Gantt data")
        self.assertEqual(task_data['type'], 'task', "Task should be type 'task' (bar)")
        self.assertEqual(task_data['end_date'], '2026-06-20', "End date should be deadline")
        self.assertEqual(task_data['start_date'], '2026-06-18', "Start should be 2 working days before Friday (Wednesday)")
        self.assertEqual(task_data['story_points'], 16.0)
        self.assertEqual(task_data['working_days'], 2)
        self.assertIsNone(task_data['duration'], "Duration should be None (calculated from start/end)")

    def test_task_without_story_points_renders_as_milestone(self):
        """Tasks without story points should render as milestones (points)."""
        task = Task.objects.create(
            title='Task without SP',
            project=self.project,
            deadline=date(2026, 6, 20),
            status='todo',
            priority=2
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        data = json.loads(response.content)
        task_data = None
        for item in data['data']:
            if item.get('task_id') == task.pk:
                task_data = item
                break

        self.assertIsNotNone(task_data, "Task not found in Gantt data")
        self.assertEqual(task_data['type'], 'milestone', "Task should be type 'milestone' (point)")
        self.assertEqual(task_data['start_date'], '2026-06-20', "Milestone start = end")
        self.assertEqual(task_data['end_date'], '2026-06-20', "Milestone end = deadline")
        self.assertEqual(task_data['duration'], 0, "Milestone duration should be 0")
        self.assertIsNone(task_data['story_points'])
        self.assertEqual(task_data['working_days'], 0)

    def test_task_weekend_skipping(self):
        """Task starting calculation should skip weekends."""
        task = Task.objects.create(
            title='Task over weekend',
            project=self.project,
            deadline=date(2026, 6, 22),  # Monday
            story_points=8,  # 1 working day
            status='in_progress'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        data = json.loads(response.content)
        task_data = None
        for item in data['data']:
            if item.get('task_id') == task.pk:
                task_data = item
                break

        self.assertIsNotNone(task_data)
        self.assertEqual(task_data['end_date'], '2026-06-22', "End should be Monday")
        self.assertEqual(task_data['start_date'], '2026-06-19', "Start should be Friday (skip weekend)")
        self.assertEqual(task_data['working_days'], 1)

    def test_task_includes_status_and_priority_labels(self):
        """Task data should include status_label and priority_label."""
        task = Task.objects.create(
            title='Task with labels',
            project=self.project,
            deadline=date(2026, 6, 20),
            story_points=8,
            status='review',
            priority=3  # High
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        data = json.loads(response.content)
        task_data = None
        for item in data['data']:
            if item.get('task_id') == task.pk:
                task_data = item
                break

        self.assertIsNotNone(task_data)
        self.assertEqual(task_data['status'], 'review')
        self.assertEqual(task_data['status_label'], 'Review')
        self.assertEqual(task_data['priority'], 3)
        self.assertEqual(task_data['priority_label'], 'High')

    def test_task_without_deadline_not_in_gantt(self):
        """Tasks without deadline should not appear in Gantt."""
        task = Task.objects.create(
            title='Task without deadline',
            project=self.project,
            story_points=8,
            status='backlog'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        data = json.loads(response.content)

        # Task should not be in the response
        for item in data['data']:
            self.assertNotEqual(item.get('task_id'), task.pk,
                               "Task without deadline should not be in Gantt")

    def test_task_with_assigned_user(self):
        """Task with assigned user should include resource info."""
        task = Task.objects.create(
            title='Assigned task',
            project=self.project,
            deadline=date(2026, 6, 20),
            story_points=8,
            assigned_to_user=self.user,
            status='todo'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:calendar-data'))

        data = json.loads(response.content)
        task_data = None
        for item in data['data']:
            if item.get('task_id') == task.pk:
                task_data = item
                break

        self.assertIsNotNone(task_data)
        self.assertEqual(task_data['resource_id'], f'u_{self.user.pk}')
        self.assertEqual(task_data['resource_label'], self.user.full_name)

        # Check resource is in resources list
        resource_found = False
        for resource in data['resources']:
            if resource['id'] == f'u_{self.user.pk}':
                resource_found = True
                self.assertEqual(resource['label'], self.user.full_name)
                self.assertEqual(resource['avatar'], self.user.initials)
        self.assertTrue(resource_found, "User resource should be in resources list")
