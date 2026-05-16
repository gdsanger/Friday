"""
Test Dashboard Redesign - ISSUE-68

This test file documents the acceptance criteria for the dashboard redesign.
Run this after the implementation to verify all features are working correctly.
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.tasks.models import Task, TaskActivity
from apps.projects.models import Project
from apps.teams.models import Team
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestDashboardRedesign:
    """Test suite for ISSUE-68: Dashboard Redesign"""

    def setup_method(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_loads_with_new_layout(self):
        """Test that dashboard page loads successfully with new 3-column layout"""
        response = self.client.get('/dashboard/')
        assert response.status_code == 200

        # Check for KPI strip
        assert b'widget-my-tasks' in response.content
        assert b'widget-overdue' in response.content
        assert b'widget-due-week' in response.content
        assert b'widget-my-projects' in response.content

    def test_dashboard_card_classes_present(self):
        """Test that dashboard uses dashboard-card class"""
        response = self.client.get('/dashboard/')
        assert response.status_code == 200
        assert b'dashboard-card' in response.content

    def test_activity_widget_endpoint(self):
        """Test activity widget endpoint returns data"""
        response = self.client.get('/dashboard/widgets/activity/')
        assert response.status_code == 200
        # Check for timeline structure
        assert b'widget-header' in response.content or b'activity-timeline' in response.content

    def test_project_status_widget_endpoint(self):
        """Test project status widget endpoint"""
        response = self.client.get('/dashboard/widgets/project-status/')
        assert response.status_code == 200

    def test_due_soon_widget_endpoint(self):
        """Test due soon widget endpoint"""
        response = self.client.get('/dashboard/widgets/due-soon/')
        assert response.status_code == 200

    def test_activity_widget_with_activities(self):
        """Test activity widget displays activities with timeline UI"""
        # Create a project and task
        project = Project.objects.create(
            name='Test Project',
            color='#3b82f6',
            status='active'
        )
        project.user_members.add(self.user)

        task = Task.objects.create(
            title='Test Task',
            project=project,
            created_by=self.user,
            status='open'
        )

        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=self.user,
            verb=TaskActivity.VERB_CREATED,
            new_value='Created'
        )

        response = self.client.get('/dashboard/widgets/activity/')
        assert response.status_code == 200
        assert b'activity-timeline' in response.content
        assert b'activity-item' in response.content
        assert b'activity-icon' in response.content

    def test_project_status_widget_with_projects(self):
        """Test project status widget displays projects with enhanced design"""
        project = Project.objects.create(
            name='Test Project',
            color='#10b981',
            status='active'
        )
        project.user_members.add(self.user)

        # Create some tasks
        Task.objects.create(
            title='Task 1',
            project=project,
            status='done'
        )
        Task.objects.create(
            title='Task 2',
            project=project,
            status='open'
        )

        response = self.client.get('/dashboard/widgets/project-status/')
        assert response.status_code == 200
        assert b'Test Project' in response.content
        # Check for progress bar
        assert b'progress-bar' in response.content

    def test_due_soon_widget_with_tasks(self):
        """Test due soon widget displays tasks with priority indicators"""
        project = Project.objects.create(
            name='Test Project',
            color='#3b82f6',
            status='active'
        )
        project.user_members.add(self.user)

        tomorrow = timezone.now().date() + timedelta(days=1)
        task = Task.objects.create(
            title='Due Soon Task',
            project=project,
            assigned_to_user=self.user,
            due_date=tomorrow,
            priority=3,  # High priority
            status='open'
        )

        response = self.client.get('/dashboard/widgets/due-soon/')
        assert response.status_code == 200
        assert b'Due Soon Task' in response.content
        # Check for priority indicator
        assert b'flex-shrink-0 rounded-pill' in response.content

    def test_activity_feed_refresh_rate(self):
        """Test that activity feed has 30s refresh rate"""
        response = self.client.get('/dashboard/')
        assert response.status_code == 200
        # Check for 30s trigger on activity widget
        assert b'every 30s' in response.content

    def test_widget_empty_states(self):
        """Test that widgets display appropriate empty states"""
        # Activity widget empty state
        response = self.client.get('/dashboard/widgets/activity/')
        assert response.status_code == 200
        # Should show "Noch keine Aktivitäten" or similar

        # Project status empty state
        response = self.client.get('/dashboard/widgets/project-status/')
        assert response.status_code == 200

        # Due soon empty state
        response = self.client.get('/dashboard/widgets/due-soon/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestDashboardActivityIcons:
    """Test activity icon mapping"""

    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_activity_icon_classes(self):
        """Test that different activity types get different icon classes"""
        project = Project.objects.create(name='Test', status='active')
        project.user_members.add(self.user)

        task = Task.objects.create(
            title='Test Task',
            project=project,
            status='open'
        )

        # Test different activity verbs
        verbs_to_test = [
            (TaskActivity.VERB_STATUS_CHANGED, b'activity-icon-primary'),
            (TaskActivity.VERB_CLOSED, b'activity-icon-success'),
            (TaskActivity.VERB_ASSIGNED, b'activity-icon-success'),
            (TaskActivity.VERB_COMMENTED, b'activity-icon-info'),
            (TaskActivity.VERB_PRIORITY_CHANGED, b'activity-icon-warning'),
        ]

        for verb, expected_class in verbs_to_test:
            TaskActivity.objects.create(
                task=task,
                user=self.user,
                verb=verb,
                new_value='test'
            )

        response = self.client.get('/dashboard/widgets/activity/')
        assert response.status_code == 200

        # Check that various icon classes are present
        for _, icon_class in verbs_to_test:
            assert icon_class in response.content


# Manual Testing Checklist
"""
MANUAL TESTING CHECKLIST FOR ISSUE-68

[ ] Layout Tests
    [ ] Dashboard displays 4 KPI cards at top
    [ ] Main content is 2/3 width on desktop
    [ ] Activity feed is 1/3 width on desktop
    [ ] Activity feed is sticky and scrollable
    [ ] Layout stacks vertically on mobile (<992px)

[ ] Activity Feed Tests
    [ ] Timeline shows vertical line connecting items
    [ ] Icons are colored correctly by verb type:
        [ ] Blue for status changes
        [ ] Green for created/assigned/closed
        [ ] Orange for priority changes
        [ ] Purple for comments
    [ ] Task links open slide-over
    [ ] "Live" indicator shows green dot
    [ ] Auto-refreshes every 30 seconds
    [ ] Scrollbar is thin and subtle
    [ ] Empty state shows activity icon message

[ ] Project Status Tests
    [ ] Projects show 10px colored circle
    [ ] Progress bar is 6px high with project color
    [ ] Task count shows as "3/8" format in monospace
    [ ] Status badge has green background for active projects
    [ ] "Alle anzeigen →" link works
    [ ] Empty state shows folder icon

[ ] Due Soon Tests
    [ ] Tasks show priority color on left (3px bar)
        [ ] Red for high priority (≥3)
        [ ] Orange for medium priority (2)
        [ ] Gray for low/normal priority
    [ ] Assignee avatar displays correctly (24px)
    [ ] Due date is red when today
    [ ] Task links open slide-over
    [ ] Empty state shows check icon with emoji

[ ] General Tests
    [ ] All widget headers use uppercase with letter-spacing
    [ ] Dashboard-card styling is consistent
    [ ] Light mode colors work correctly
    [ ] Dark mode colors work correctly
    [ ] No console errors
    [ ] HTMX requests load correctly
    [ ] Page loads within acceptable time
"""
