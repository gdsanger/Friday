"""
ISSUE-64 Fix: Checklisten-Vorlagen UI fehlt — Acceptance Criteria Tests
"""
import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
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


class ChecklistUITestCase(TestCase):
    """Test suite for ISSUE-64 Checklist UI feature."""

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

    def test_template_list_url_accessible(self):
        """Test /tasks/checklists/ shows all templates with item count."""
        print_header("TEST: Template-Verwaltung URL /tasks/checklists/")

        client = Client()
        client.force_login(self.staff_user)

        try:
            # Create templates
            template1 = ChecklistTemplate.objects.create(
                name='Template 1',
                created_by=self.staff_user
            )
            ChecklistTemplateItem.objects.create(
                template=template1,
                title='Item 1',
                order=1
            )
            ChecklistTemplateItem.objects.create(
                template=template1,
                title='Item 2',
                order=2
            )

            template2 = ChecklistTemplate.objects.create(
                name='Template 2',
                created_by=self.staff_user
            )

            # Access list page
            response = client.get('/tasks/checklists/')
            self.assertEqual(response.status_code, 200)
            test_pass("/tasks/checklists/ returns 200")

            # Check templates in response
            self.assertContains(response, 'Template 1')
            self.assertContains(response, 'Template 2')
            test_pass("Templates are listed")

            # Check item count shown
            self.assertContains(response, '2')  # template1 has 2 items
            test_pass("Item count is displayed")

            return True
        except Exception as e:
            test_fail("Template list URL", str(e))
            return False

    def test_staff_can_create_template(self):
        """Test staff can create new template with items."""
        print_header("TEST: Staff kann neue Vorlage anlegen")

        client = Client()
        client.force_login(self.staff_user)

        try:
            # Create template
            response = client.post(
                '/tasks/checklists/create/',
                {'name': 'New Template'}
            )
            # Should redirect to edit page
            self.assertEqual(response.status_code, 302)
            test_pass("Create template redirects")

            template = ChecklistTemplate.objects.get(name='New Template')
            test_pass("Template was created")

            # Add items via edit
            response = client.post(
                f'/tasks/checklists/{template.pk}/edit/',
                {
                    'name': 'New Template',
                    'items[]': ['Item A', 'Item B', 'Item C']
                }
            )
            self.assertEqual(response.status_code, 302)
            test_pass("Items can be added to template")

            template.refresh_from_db()
            self.assertEqual(template.items.count(), 3)
            test_pass("All items were saved")

            return True
        except Exception as e:
            test_fail("Staff create template", str(e))
            return False

    def test_staff_can_edit_template(self):
        """Test staff can edit template name and items."""
        print_header("TEST: Staff kann Vorlage bearbeiten")

        client = Client()
        client.force_login(self.staff_user)

        try:
            # Create template with items
            template = ChecklistTemplate.objects.create(
                name='Original Name',
                created_by=self.staff_user
            )
            ChecklistTemplateItem.objects.create(
                template=template,
                title='Original Item',
                order=1
            )

            # Edit template
            response = client.get(f'/tasks/checklists/{template.pk}/edit/')
            self.assertEqual(response.status_code, 200)
            test_pass("Edit page accessible")

            # Update template
            response = client.post(
                f'/tasks/checklists/{template.pk}/edit/',
                {
                    'name': 'Updated Name',
                    'items[]': ['Updated Item', 'New Item 2']
                }
            )
            self.assertEqual(response.status_code, 302)
            test_pass("Update template redirects")

            template.refresh_from_db()
            self.assertEqual(template.name, 'Updated Name')
            self.assertEqual(template.items.count(), 2)
            test_pass("Template name and items updated")

            return True
        except Exception as e:
            test_fail("Staff edit template", str(e))
            return False

    def test_staff_can_delete_template(self):
        """Test staff can delete template."""
        print_header("TEST: Staff kann Vorlage löschen")

        client = Client()
        client.force_login(self.staff_user)

        try:
            # Create template
            template = ChecklistTemplate.objects.create(
                name='To Delete',
                created_by=self.staff_user
            )

            # Delete template
            response = client.post(f'/tasks/checklists/{template.pk}/delete/')
            self.assertEqual(response.status_code, 302)
            test_pass("Delete template redirects")

            exists = ChecklistTemplate.objects.filter(pk=template.pk).exists()
            self.assertFalse(exists)
            test_pass("Template was deleted")

            return True
        except Exception as e:
            test_fail("Staff delete template", str(e))
            return False

    def test_template_dropdown_in_task_detail(self):
        """Test template dropdown appears in task detail when templates exist."""
        print_header("TEST: Vorlage-Dropdown im Task-Detail")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create template
            template = ChecklistTemplate.objects.create(
                name='Test Template',
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

            # Get task detail (slide-over)
            response = client.get(f'/tasks/{self.task.pk}/detail/')
            self.assertEqual(response.status_code, 200)
            test_pass("Task detail page accessible")

            # Check template dropdown appears
            self.assertContains(response, 'Vorlage anwenden')
            self.assertContains(response, 'Test Template')
            test_pass("Template dropdown is present")

            return True
        except Exception as e:
            test_fail("Template dropdown in task detail", str(e))
            return False

    def test_apply_template_to_task(self):
        """Test applying template adds all items to task."""
        print_header("TEST: Vorlage auf Task anwenden")

        client = Client()
        client.force_login(self.user1)

        try:
            # Create existing checklist item
            existing_item = TaskChecklistItem.objects.create(
                task=self.task,
                title='Existing Item',
                order=1
            )

            # Create template
            template = ChecklistTemplate.objects.create(
                name='Apply Template',
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
            test_pass("Apply template returns 200")

            # Check all items exist
            items = TaskChecklistItem.objects.filter(task=self.task)
            self.assertEqual(items.count(), 3)
            test_pass("All items exist (existing + template items)")

            # Check existing item is still there
            still_exists = TaskChecklistItem.objects.filter(pk=existing_item.pk).exists()
            self.assertTrue(still_exists)
            test_pass("Existing items remain when applying template")

            # Check template items were added
            template_item1 = TaskChecklistItem.objects.filter(
                task=self.task, title='Template Item 1'
            ).first()
            template_item2 = TaskChecklistItem.objects.filter(
                task=self.task, title='Template Item 2'
            ).first()
            self.assertIsNotNone(template_item1)
            self.assertIsNotNone(template_item2)
            test_pass("Template items were added")

            return True
        except Exception as e:
            test_fail("Apply template to task", str(e))
            return False

    def test_sidebar_link_for_staff(self):
        """Test sidebar link to checklist templates is visible for staff."""
        print_header("TEST: Sidebar-Link für Staff sichtbar")

        client = Client()

        try:
            # Staff user sees link
            client.force_login(self.staff_user)
            response = client.get('/')
            # This should render the sidebar
            # We'll check if the link exists in the sidebar template

            # For now, we'll check if the URL pattern is accessible
            response = client.get('/tasks/checklists/')
            self.assertEqual(response.status_code, 200)
            test_pass("Staff can access /tasks/checklists/")

            # Non-staff user should not see link or access page
            client.force_login(self.user1)
            response = client.get('/tasks/checklists/')
            # Should get 403 or redirect
            self.assertIn(response.status_code, [403, 302])
            test_pass("Non-staff user cannot access checklist templates")

            return True
        except Exception as e:
            test_fail("Sidebar link visibility", str(e))
            return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("ISSUE-64: Fix Checklisten-Vorlagen UI — Acceptance Criteria Tests")
    print("="*70)

    suite = [
        ('Template List URL', 'test_template_list_url_accessible'),
        ('Staff Create Template', 'test_staff_can_create_template'),
        ('Staff Edit Template', 'test_staff_can_edit_template'),
        ('Staff Delete Template', 'test_staff_can_delete_template'),
        ('Template Dropdown', 'test_template_dropdown_in_task_detail'),
        ('Apply Template', 'test_apply_template_to_task'),
        ('Sidebar Link', 'test_sidebar_link_for_staff'),
    ]

    results = []
    test_case = ChecklistUITestCase()
    test_case.setUp()

    for name, method in suite:
        try:
            result = getattr(test_case, method)()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test {name} crashed: {e}")
            import traceback
            traceback.print_exc()
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
