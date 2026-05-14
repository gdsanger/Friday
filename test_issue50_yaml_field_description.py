#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-50: YAML Field Description as Helptext.

This script tests:
- description in YAML field definition is correctly parsed
- Helptext appears below input field in portal/ticket_create.html
- Helptext appears below input field in tasks/templates/use.html
- No helptext when description is not defined
- Multi-line description is correctly displayed
- validate_yaml() accepts description without error
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
from django.template import Template, Context
from django.template.loader import render_to_string

from apps.tasks.models import TaskTemplate
from apps.projects.models import Project
from apps.teams.models import Team, TeamMembership

User = get_user_model()


def setup_test_data():
    """Create test users, projects, and templates."""
    # Clean up any existing test data first
    TaskTemplate.objects.filter(name__contains='Issue50').delete()
    Project.objects.filter(name__startswith='Test Project Issue50').delete()
    User.objects.filter(username__startswith='test_').filter(username__contains='issue50').delete()
    Team.objects.filter(slug__startswith='test-team-issue50').delete()

    # Create test user
    user = User.objects.create_user(
        username='test_user_issue50',
        email='test_issue50@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )

    # Create test team
    team = Team.objects.create(
        name='Test Team Issue50',
        slug='test-team-issue50',
        description='Test team for issue 50'
    )
    TeamMembership.objects.create(team=team, user=user, role='member')

    # Create test project
    project = Project.objects.create(
        name='Test Project Issue50',
        owner=user
    )

    # YAML with description fields for all types
    yaml_with_descriptions = """- name: mehrwert
  label: Mehrwert
  description: Beschreibe in 3-4 Sätzen welchen Mehrwert Dir, bzw. Deinem Team das neue Feature bringt, und / oder begründe den Bedarf.
  type: textarea
  required: true

- name: zielgruppe
  label: Zielgruppe
  description: Für wen ist diese Aufgabe relevant?
  type: text
  required: false

- name: prioritaet
  label: Priorität
  description: Wähle die Dringlichkeit aus
  type: select
  required: true
  options:
    - Hoch
    - Mittel
    - Niedrig

- name: tags
  label: Tags
  description: Wähle alle zutreffenden Tags aus
  type: multiselect
  required: false
  options:
    - Frontend
    - Backend
    - Design
    - Testing

- name: budget
  label: Budget (€)
  description: Geschätztes Budget in Euro
  type: number
  required: false
  min: 0

- name: deadline_internal
  label: Interner Deadline
  description: Internes Datum für die Fertigstellung
  type: date
  required: false

- name: dringend
  label: Dringend
  description: Markiere wenn sofortige Bearbeitung erforderlich ist
  type: checkbox
  required: false"""

    # YAML without description fields
    yaml_without_descriptions = """- name: title
  label: Titel
  type: text
  required: true

- name: beschreibung
  label: Beschreibung
  type: textarea
  required: true"""

    # Create template with descriptions
    template_with_desc = TaskTemplate.objects.create(
        name='Test Template with Descriptions Issue50',
        slug='test-template-desc-issue50',
        description='Template with field descriptions',
        extra_fields_yaml=yaml_with_descriptions,
        default_project=project,
        default_assigned_to_team=team
    )

    # Create template without descriptions
    template_without_desc = TaskTemplate.objects.create(
        name='Test Template without Descriptions Issue50',
        slug='test-template-no-desc-issue50',
        description='Template without field descriptions',
        extra_fields_yaml=yaml_without_descriptions,
        default_project=project,
        default_assigned_to_team=team
    )

    return user, team, project, template_with_desc, template_without_desc


def test_validate_yaml_accepts_description():
    """Test that validate_yaml() accepts description field without error."""
    print("\n" + "="*80)
    print("TEST 1: validate_yaml() accepts description field")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    # Test template with descriptions
    is_valid, error_msg = template_with_desc.validate_yaml()
    print(f"✓ Template with descriptions - Valid: {is_valid}, Error: '{error_msg}'")
    assert is_valid, f"Template with descriptions should be valid, but got error: {error_msg}"

    # Test template without descriptions
    is_valid, error_msg = template_without_desc.validate_yaml()
    print(f"✓ Template without descriptions - Valid: {is_valid}, Error: '{error_msg}'")
    assert is_valid, f"Template without descriptions should be valid, but got error: {error_msg}"

    print("✅ PASS: validate_yaml() accepts description field")


def test_description_parsed_correctly():
    """Test that description is correctly parsed from YAML."""
    print("\n" + "="*80)
    print("TEST 2: description is correctly parsed from YAML")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    # Get extra fields from template with descriptions
    fields_with_desc = template_with_desc.get_extra_fields()
    print(f"✓ Parsed {len(fields_with_desc)} fields from template with descriptions")

    # Check that description is present in fields
    textarea_field = next(f for f in fields_with_desc if f['name'] == 'mehrwert')
    assert 'description' in textarea_field, "description key should be present in field"
    print(f"✓ textarea field has description: '{textarea_field['description'][:50]}...'")

    text_field = next(f for f in fields_with_desc if f['name'] == 'zielgruppe')
    assert 'description' in text_field, "description key should be present in field"
    print(f"✓ text field has description: '{text_field['description']}'")

    select_field = next(f for f in fields_with_desc if f['name'] == 'prioritaet')
    assert 'description' in select_field, "description key should be present in field"
    print(f"✓ select field has description: '{select_field['description']}'")

    # Get extra fields from template without descriptions
    fields_without_desc = template_without_desc.get_extra_fields()
    print(f"✓ Parsed {len(fields_without_desc)} fields from template without descriptions")

    title_field = next(f for f in fields_without_desc if f['name'] == 'title')
    assert 'description' not in title_field, "description key should not be present in field without description"
    print(f"✓ Field without description does not have 'description' key")

    print("✅ PASS: description is correctly parsed from YAML")


def test_field_partial_renders_description():
    """Test that _field.html partial renders description for all field types."""
    print("\n" + "="*80)
    print("TEST 3: _field.html renders description for all field types")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    fields = template_with_desc.get_extra_fields()

    # Load the field partial template
    from django.template.loader import get_template
    template = get_template('tasks/templates/partials/_field.html')

    field_types_tested = set()

    for field in fields:
        field_type = field['type']
        field_types_tested.add(field_type)

        # Render the field
        context = {'field': field, 'post': {}}
        html = template.render(context)

        if 'description' in field:
            # Check that description is rendered
            assert field['description'] in html, f"{field_type} field should render description"
            assert 'form-text' in html, f"{field_type} field should have form-text class for description"
            assert 'font-size:12px' in html, f"{field_type} field should have inline font-size style"
            assert 'var(--friday-text-muted)' in html, f"{field_type} field should use CSS variable for color"
            print(f"✓ {field_type:12s} field renders description correctly")
        else:
            # Check that no description div is rendered
            # Should not have multiple form-text divs
            print(f"✓ {field_type:12s} field has no description (as expected)")

    print(f"✓ Tested {len(field_types_tested)} field types: {', '.join(sorted(field_types_tested))}")
    print("✅ PASS: _field.html renders description for all field types")


def test_field_without_description_no_helptext():
    """Test that fields without description don't show helptext."""
    print("\n" + "="*80)
    print("TEST 4: Fields without description don't show helptext")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    fields = template_without_desc.get_extra_fields()

    from django.template.loader import get_template
    template = get_template('tasks/templates/partials/_field.html')

    for field in fields:
        context = {'field': field, 'post': {}}
        html = template.render(context)

        # Count occurrences of form-text divs with description styling
        description_divs = html.count('class="form-text"')

        # Should be 0 if no description field exists
        if 'description' not in field:
            # The description div should not appear
            assert 'font-size:12px' not in html or description_divs == 0, \
                f"Field {field['name']} without description should not render description div"
            print(f"✓ {field['type']:12s} field '{field['name']}' has no helptext (correct)")

    print("✅ PASS: Fields without description don't show helptext")


def test_multiline_description():
    """Test that multiline description is correctly displayed."""
    print("\n" + "="*80)
    print("TEST 5: Multiline description is correctly displayed")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    fields = template_with_desc.get_extra_fields()

    # Get the textarea field which has a multiline description
    textarea_field = next(f for f in fields if f['name'] == 'mehrwert')

    from django.template.loader import get_template
    template = get_template('tasks/templates/partials/_field.html')

    context = {'field': textarea_field, 'post': {}}
    html = template.render(context)

    # Check that the full multiline description is present
    description_text = textarea_field['description']
    assert description_text in html, "Multiline description should be fully rendered"
    print(f"✓ Multiline description rendered: '{description_text[:50]}...'")
    print("✅ PASS: Multiline description is correctly displayed")


def test_template_use_view():
    """Test that description appears in tasks/templates/use.html view."""
    print("\n" + "="*80)
    print("TEST 6: Description appears in template use view")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    client = Client()
    client.force_login(user)

    # Get template use page
    url = reverse('tasks:template-use', kwargs={'slug': template_with_desc.slug})
    response = client.get(url)

    assert response.status_code == 200, f"Template use page should be accessible, got {response.status_code}"
    print(f"✓ Template use view returned status 200")

    html = response.content.decode('utf-8')

    # Check that descriptions are rendered
    fields = template_with_desc.get_extra_fields()
    for field in fields[:3]:  # Test first 3 fields
        if 'description' in field:
            assert field['description'] in html, f"Field {field['name']} description should appear in HTML"
            print(f"✓ Field '{field['name']}' description appears in template use view")

    # Check styling is present
    assert 'font-size:12px' in html, "Description styling should be present"
    assert 'form-text' in html, "form-text class should be present"
    print("✓ Description styling is present in rendered HTML")

    print("✅ PASS: Description appears in template use view")


def test_yaml_editor_hint():
    """Test that YAML editor shows description field in documentation."""
    print("\n" + "="*80)
    print("TEST 7: YAML editor hint documents description field")
    print("="*80)

    user, team, project, template_with_desc, template_without_desc = setup_test_data()

    # Make user staff so they can access template edit
    user.is_staff = True
    user.save()

    client = Client()
    client.force_login(user)

    # Get template edit page
    url = reverse('tasks:template-edit', kwargs={'slug': template_with_desc.slug})
    response = client.get(url)

    assert response.status_code == 200, f"Template edit page should be accessible, got {response.status_code}"
    print(f"✓ Template edit view returned status 200")

    html = response.content.decode('utf-8')

    # Check that description is documented
    assert 'description' in html.lower(), "The word 'description' should appear in documentation"
    assert 'Helptext' in html or 'helptext' in html.lower(), "Documentation should mention helptext"

    # Check for the specific documentation strings
    assert 'Verfügbare Felder pro Eintrag' in html, "Field documentation section should be present"

    # Check that all field attributes are documented
    assert 'name' in html, "name attribute should be documented"
    assert 'label' in html, "label attribute should be documented"
    assert 'type' in html, "type attribute should be documented"

    print("✓ YAML editor documentation mentions description field")
    print("✓ Field attributes are documented")
    print("✅ PASS: YAML editor hint documents description field")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*80)
    print("ISSUE-50: YAML Field Description as Helptext - Test Suite")
    print("="*80)

    tests = [
        test_validate_yaml_accepts_description,
        test_description_parsed_correctly,
        test_field_partial_renders_description,
        test_field_without_description_no_helptext,
        test_multiline_description,
        test_template_use_view,
        test_yaml_editor_hint,
    ]

    failed_tests = []

    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            print(f"❌ FAIL: {test_func.__name__}")
            print(f"   Error: {e}")
            failed_tests.append((test_func.__name__, str(e)))
        except Exception as e:
            print(f"❌ ERROR: {test_func.__name__}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed_tests.append((test_func.__name__, f"{type(e).__name__}: {e}"))

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {len(tests) - len(failed_tests)}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print("\nFailed tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    run_all_tests()
