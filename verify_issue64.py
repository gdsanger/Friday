#!/usr/bin/env python
"""
Quick verification script for ISSUE-64 fixes.
Checks that all required files and patterns exist.
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} NOT FOUND")
        return False

def check_file_contains(filepath, pattern, description):
    """Check if a file contains a specific pattern."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if pattern in content:
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description}: Pattern not found in {filepath}")
                return False
    except FileNotFoundError:
        print(f"✗ {description}: File {filepath} not found")
        return False

def main():
    print("="*70)
    print("ISSUE-64: Checklist Template UI Verification")
    print("="*70)

    base_path = '/home/runner/work/Friday/Friday'
    results = []

    # Check template files exist
    print("\n1. Checking template files...")
    results.append(check_file_exists(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        "Template list file exists"
    ))
    results.append(check_file_exists(
        f"{base_path}/templates/tasks/checklists/template_form.html",
        "Template create form file exists"
    ))
    results.append(check_file_exists(
        f"{base_path}/templates/tasks/checklists/template_edit.html",
        "Template edit form file exists"
    ))
    results.append(check_file_exists(
        f"{base_path}/templates/tasks/partials/checklist.html",
        "Checklist partial file exists"
    ))

    # Check template_list.html has correct structure
    print("\n2. Checking template_list.html structure...")
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        'Checklisten-Vorlagen',
        "List template has title"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        'table table-sm',
        "List template uses table layout"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        'tpl.items.count',
        "List template shows item count"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        'checklist-template-edit',
        "List template has edit link"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_list.html",
        'checklist-template-delete',
        "List template has delete button"
    ))

    # Check template_form.html has correct structure
    print("\n3. Checking template_form.html (create) structure...")
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_form.html",
        'Neue Vorlage',
        "Create form has title"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_form.html",
        'checklist-template-list',
        "Create form has back link"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_form.html",
        'name="name"',
        "Create form has name field"
    ))

    # Check template_edit.html has correct structure
    print("\n4. Checking template_edit.html structure...")
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_edit.html",
        'Vorlage bearbeiten',
        "Edit form has title"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_edit.html",
        'name="items[]"',
        "Edit form has items field"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_edit.html",
        'addTemplateItem',
        "Edit form has add item button"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/checklists/template_edit.html",
        'template-item-row',
        "Edit form has item rows"
    ))

    # Check checklist.html has template dropdown
    print("\n5. Checking checklist.html template dropdown...")
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/partials/checklist.html",
        'Vorlage anwenden',
        "Checklist has template dropdown"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/partials/checklist.html",
        'checklist-apply-template',
        "Checklist has apply template URL"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/partials/checklist.html",
        'tpl.items.count',
        "Template dropdown shows item count"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/tasks/partials/checklist.html",
        'Anwenden',
        "Template dropdown has apply button"
    ))

    # Check sidebar has checklist link
    print("\n6. Checking sidebar link...")
    results.append(check_file_contains(
        f"{base_path}/templates/partials/sidebar.html",
        'checklist-template-list',
        "Sidebar has checklist template link"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/partials/sidebar.html",
        'bi-list-check',
        "Sidebar link has correct icon"
    ))
    results.append(check_file_contains(
        f"{base_path}/templates/partials/sidebar.html",
        'Checklisten',
        "Sidebar link has correct text"
    ))

    # Check URLs are registered
    print("\n7. Checking URL configuration...")
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/urls.py",
        "path('checklists/',",
        "Template list URL registered"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/urls.py",
        "path('checklists/create/',",
        "Template create URL registered"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/urls.py",
        "path('checklists/<int:pk>/edit/',",
        "Template edit URL registered"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/urls.py",
        "path('checklists/<int:pk>/delete/',",
        "Template delete URL registered"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/urls.py",
        "checklist-apply-template",
        "Apply template URL registered"
    ))

    # Check views exist
    print("\n8. Checking view implementations...")
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/views.py",
        "ChecklistTemplateListView",
        "Template list view exists"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/views.py",
        "ChecklistTemplateCreateView",
        "Template create view exists"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/views.py",
        "ChecklistTemplateEditView",
        "Template edit view exists"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/views.py",
        "ChecklistTemplateDeleteView",
        "Template delete view exists"
    ))
    results.append(check_file_contains(
        f"{base_path}/apps/tasks/views.py",
        "ChecklistApplyTemplateView",
        "Apply template view exists"
    ))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} checks")

    if passed == total:
        print("\n✓ All verification checks passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} check(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
