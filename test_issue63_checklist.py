"""
ISSUE-63 Checklisten in Tasks — Acceptance Criteria Tests
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from apps.projects.models import Project, ProjectUserMembership
from apps.tasks.models import Task, ChecklistTemplate, ChecklistTemplateItem, TaskChecklistItem

User = get_user_model()


def print_header(text):
    print(f"\n{'='*70}")
    print(text)
    print('='*70)


def test_pass(desc):
    print(f"✓ {desc}")
    return True


def test_fail(desc, error):
    print(f"✗ {desc}: {error}")
    return False


class ChecklistTestCase(TestCase):
    """Test suite for ISSUE-63 Checklists feature."""

    def setUp(self):
        """Create test users, projects, and tasks."""
        # Clean up first
        User.objects.filter(username__startswith='testuser').delete()
        Project.objects.filter(name__startswith='Test ').delete()
        ChecklistTemplate.objects.filter(name__startswith='Test ').delete()

        # Create users
        self.user1 = User.objects.create_user(
            username='testuser1', email='testuser1@test.com', password='test'
        )
        self.staff_user = User.objects.create_user(
            username='teststaff', email='teststaff@test.com', password='test', is_staff=True
        )

        # Create project
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            status='active',
            owner=self.user1
        )
        ProjectUserMembership.objects.create(
            project=self.project,
            user=self.user1,
            role='manager'
        )

        # Create task
        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            status=Task.STATUS_TODO,
            created_by=self.user1
        )

    def test_models_exist(self):
        """Test that checklist models exist and are properly configured."""
        print_header("TEST: Modelle existieren")

        try:
            # Test ChecklistTemplate
            template = ChecklistTemplate.objects.create(
                name='Test Template',
                created_by=self.staff_user
            )
            test_pass("ChecklistTemplate model exists")

            # Test ChecklistTemplateItem
            item = ChecklistTemplateItem.objects.create(
                template=template,
                title='Test Item',
                order=1
            )
            test_pass("ChecklistTemplateItem model exists")

            # Test TaskChecklistItem
            task_item = TaskChecklistItem.objects.create(
                task=self.task,
                title='Task Item',
                order=1
            )
            test_pass("TaskChecklistItem model exists")

            # Test ordering
            self.assertEqual(template.items.first(), item)
            test_pass("ChecklistTemplateItem ordering works")

            self.assertEqual(self.task.checklist_items.first(), task_item)
            test_pass("TaskChecklistItem ordering works")

            return True
        except Exception as e:
            test_fail("Models test", str(e))
            return False

    def test_task_checklist_properties(self):
        """Test Task model checklist helper properties."""
        print_header("TEST: Task Checklist Properties")

        try:
            # Create checklist items
            item1 = TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 1',
                is_done=True,
                order=1
            )
            item2 = TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 2',
                is_done=False,
                order=2
            )
            item3 = TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 3',
                is_done=True,
                order=3
            )

            # Test checklist_progress
            done, total = self.task.checklist_progress
            self.assertEqual(done, 2)
            self.assertEqual(total, 3)
            test_pass("checklist_progress returns correct (done, total)")

            # Test checklist_pct
            pct = self.task.checklist_pct
            self.assertEqual(pct, 66)  # 2/3 = 0.666... = 66%
            test_pass("checklist_pct returns correct percentage")

            # Test with empty checklist
            TaskChecklistItem.objects.all().delete()
            done, total = self.task.checklist_progress
            self.assertEqual(done, 0)
            self.assertEqual(total, 0)
            pct = self.task.checklist_pct
            self.assertEqual(pct, 0)
            test_pass("Properties work correctly with empty checklist")

            return True
        except Exception as e:
            test_fail("Checklist properties", str(e))
            return False

    def test_checklist_item_add(self):
        """Test adding checklist items via HTMX view."""
        print_header("TEST: Checklist Item hinzufügen")

        client = Client()
        client.force_login(self.user1)

        try:
            # Add item
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/add/',
                {'title': 'New Item'},
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)
            test_pass("POST to checklist-item-add returns 200")

            # Check item was created
            item = TaskChecklistItem.objects.filter(task=self.task, title='New Item').first()
            self.assertIsNotNone(item)
            self.assertFalse(item.is_done)
            test_pass("Checklist item was created correctly")

            # Check order
            self.assertEqual(item.order, 1)
            test_pass("Item order is set correctly")

            return True
        except Exception as e:
            test_fail("Add checklist item", str(e))
            return False

    def test_checklist_item_toggle(self):
        """Test toggling checklist item completion."""
        print_header("TEST: Checklist Item abhaken/öffnen")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create item
            item = TaskChecklistItem.objects.create(
                task=self.task,
                title='Toggle Test',
                is_done=False,
                order=1
            )

            # Toggle to done
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/{item.pk}/toggle/',
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)
            test_pass("POST to checklist-item-toggle returns 200")

            # Check item is done
            item.refresh_from_db()
            self.assertTrue(item.is_done)
            self.assertEqual(item.done_by, self.user1)
            self.assertIsNotNone(item.done_at)
            test_pass("Item marked as done with done_by and done_at set")

            # Toggle back to not done
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/{item.pk}/toggle/',
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)

            item.refresh_from_db()
            self.assertFalse(item.is_done)
            self.assertIsNone(item.done_by)
            self.assertIsNone(item.done_at)
            test_pass("Item marked as not done with done_by and done_at cleared")

            return True
        except Exception as e:
            test_fail("Toggle checklist item", str(e))
            return False

    def test_checklist_item_delete(self):
        """Test deleting checklist items."""
        print_header("TEST: Checklist Item löschen")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create item
            item = TaskChecklistItem.objects.create(
                task=self.task,
                title='Delete Test',
                order=1
            )

            # Delete item
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/{item.pk}/delete/',
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)
            test_pass("POST to checklist-item-delete returns 200")

            # Check item was deleted
            exists = TaskChecklistItem.objects.filter(pk=item.pk).exists()
            self.assertFalse(exists)
            test_pass("Checklist item was deleted")

            return True
        except Exception as e:
            test_fail("Delete checklist item", str(e))
            return False

    def test_checklist_item_convert_to_subtask(self):
        """Test converting checklist item to subtask."""
        print_header("TEST: Checklist Item in SubTask umwandeln")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create item
            item = TaskChecklistItem.objects.create(
                task=self.task,
                title='Convert to SubTask',
                order=1
            )

            # Convert to subtask
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/{item.pk}/convert/',
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)
            test_pass("POST to checklist-item-convert returns 200")

            # Check item was deleted
            exists = TaskChecklistItem.objects.filter(pk=item.pk).exists()
            self.assertFalse(exists)
            test_pass("Checklist item was deleted after conversion")

            # Check subtask was created
            subtask = Task.objects.filter(
                parent_task=self.task,
                title='Convert to SubTask'
            ).first()
            self.assertIsNotNone(subtask)
            self.assertEqual(subtask.project, self.task.project)
            self.assertEqual(subtask.status, Task.STATUS_BACKLOG)
            self.assertEqual(subtask.created_by, self.user1)
            test_pass("SubTask was created correctly")

            return True
        except Exception as e:
            test_fail("Convert checklist item to subtask", str(e))
            return False

    def test_checklist_template_apply(self):
        """Test applying checklist template to task."""
        print_header("TEST: Vorlage auf Task anwenden")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create template with items
            template = ChecklistTemplate.objects.create(
                name='Test Template Apply',
                created_by=self.staff_user
            )
            ChecklistTemplateItem.objects.create(
                template=template,
                title='Template Item 1',
                order=1
            )
            ChecklistTemplateItem.objects.create(
                template=template,
                title='Template Item 2',
                order=2
            )

            # Apply template
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/apply-template/',
                {'template_id': template.pk},
                HTTP_HX_REQUEST='true'
            )
            self.assertEqual(response.status_code, 200)
            test_pass("POST to checklist-apply-template returns 200")

            # Check items were created
            items = TaskChecklistItem.objects.filter(task=self.task).order_by('order')
            self.assertEqual(items.count(), 2)
            self.assertEqual(items[0].title, 'Template Item 1')
            self.assertEqual(items[1].title, 'Template Item 2')
            test_pass("Template items were added to task")

            # Test applying template again (items should be added, not replaced)
            response = client.post(
                f'/tasks/{self.task.pk}/checklist/apply-template/',
                {'template_id': template.pk},
                HTTP_HX_REQUEST='true'
            )
            items = TaskChecklistItem.objects.filter(task=self.task)
            self.assertEqual(items.count(), 4)
            test_pass("Template can be applied multiple times")

            return True
        except Exception as e:
            test_fail("Apply checklist template", str(e))
            return False

    def test_checklist_template_management(self):
        """Test checklist template CRUD operations."""
        print_header("TEST: Checklisten-Vorlagen Verwaltung")

        client = Client()
        client.force_login(self.staff_user)

        try:
            # List templates
            response = client.get('/tasks/checklists/')
            self.assertEqual(response.status_code, 200)
            test_pass("GET checklist template list returns 200")

            # Create template form
            response = client.get('/tasks/checklists/create/')
            self.assertEqual(response.status_code, 200)
            test_pass("GET checklist template create form returns 200")

            # Create template
            response = client.post(
                '/tasks/checklists/create/',
                {'name': 'New Template'}
            )
            # Should redirect to edit page
            self.assertEqual(response.status_code, 302)
            test_pass("POST checklist template create redirects")

            template = ChecklistTemplate.objects.get(name='New Template')
            test_pass("Template was created")

            # Edit template
            response = client.get(f'/tasks/checklists/{template.pk}/edit/')
            self.assertEqual(response.status_code, 200)
            test_pass("GET checklist template edit returns 200")

            # Update template
            response = client.post(
                f'/tasks/checklists/{template.pk}/edit/',
                {
                    'name': 'Updated Template',
                    'items[]': ['Item 1', 'Item 2', 'Item 3']
                }
            )
            self.assertEqual(response.status_code, 302)
            test_pass("POST checklist template edit redirects")

            template.refresh_from_db()
            self.assertEqual(template.name, 'Updated Template')
            self.assertEqual(template.items.count(), 3)
            test_pass("Template was updated correctly")

            # Delete template
            response = client.post(f'/tasks/checklists/{template.pk}/delete/')
            self.assertEqual(response.status_code, 302)
            test_pass("POST checklist template delete redirects")

            exists = ChecklistTemplate.objects.filter(pk=template.pk).exists()
            self.assertFalse(exists)
            test_pass("Template was deleted")

            return True
        except Exception as e:
            test_fail("Template management", str(e))
            return False

    def test_template_filters(self):
        """Test template filters for checklist counts."""
        print_header("TEST: Template Tags")

        from apps.core.templatetags.friday_tags import checklist_done, checklist_total

        try:
            # Create checklist items
            TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 1',
                is_done=True,
                order=1
            )
            TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 2',
                is_done=False,
                order=2
            )
            TaskChecklistItem.objects.create(
                task=self.task,
                title='Item 3',
                is_done=True,
                order=3
            )

            # Test filters
            done = checklist_done(self.task)
            total = checklist_total(self.task)

            self.assertEqual(done, 2)
            self.assertEqual(total, 3)
            test_pass("Template filters return correct counts")

            return True
        except Exception as e:
            test_fail("Template filters", str(e))
            return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("ISSUE-63: Checklisten in Tasks — Acceptance Criteria Tests")
    print("="*70)

    suite = [
        ('Models', 'test_models_exist'),
        ('Task Properties', 'test_task_checklist_properties'),
        ('Add Item', 'test_checklist_item_add'),
        ('Toggle Item', 'test_checklist_item_toggle'),
        ('Delete Item', 'test_checklist_item_delete'),
        ('Convert to SubTask', 'test_checklist_item_convert_to_subtask'),
        ('Apply Template', 'test_checklist_template_apply'),
        ('Template Management', 'test_checklist_template_management'),
        ('Template Tags', 'test_template_filters'),
    ]

    results = []
    test_case = ChecklistTestCase()
    test_case.setUp()

    for name, method in suite:
        try:
            result = getattr(test_case, method)()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print_header("ZUSAMMENFASSUNG")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nErgebnis: {passed}/{total} Tests bestanden")

    if passed == total:
        print("\n🎉 Alle Tests erfolgreich!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} Test(s) fehlgeschlagen")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
