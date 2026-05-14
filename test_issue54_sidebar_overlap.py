#!/usr/bin/env python
"""
Visual verification test for ISSUE-54: Fix Sidebar Overlap

This test verifies that the CSS changes correctly implement the flexbox layout
to prevent sidebar overlap with main content.

Acceptance Criteria:
✅ Sidebar and Main do not overlap
✅ Sidebar collapsed → Main becomes wider (takes available space)
✅ Sidebar expanded → Main becomes narrower
✅ Transition is smooth (0.22s)
✅ Tablet: Sidebar fixed 64px, Main has margin-left: 64px
✅ Mobile: Sidebar off-screen, Main full-width
✅ No horizontal scroll on Main content area

Note: This is a CSS-only fix. Since we're testing visual layout,
manual browser testing is required. This script documents the expected behavior.
"""

import os
import sys
import re

def verify_css_changes():
    """Verify that the CSS file contains the required changes"""
    print("\n" + "="*60)
    print("ISSUE-54: Sidebar Overlap Fix - CSS Verification")
    print("="*60)

    css_file = 'static/css/friday.css'

    if not os.path.exists(css_file):
        print(f"❌ ERROR: {css_file} not found")
        return False

    with open(css_file, 'r') as f:
        content = f.read()

    tests = []

    # Test 1: Desktop sidebar should use position: relative
    print("\n1. Testing desktop sidebar positioning...")
    desktop_pattern = r'\.friday-sidebar\s*\{[^}]*position:\s*relative[^}]*\}'
    if re.search(desktop_pattern, content, re.DOTALL):
        print("   ✅ Desktop sidebar uses position: relative")
        tests.append(True)
    else:
        print("   ❌ Desktop sidebar should use position: relative")
        tests.append(False)

    # Test 2: Desktop sidebar should have flex-shrink: 0
    print("\n2. Testing desktop sidebar flex behavior...")
    flex_pattern = r'\.friday-sidebar\s*\{[^}]*flex-shrink:\s*0[^}]*\}'
    if re.search(flex_pattern, content, re.DOTALL):
        print("   ✅ Desktop sidebar has flex-shrink: 0")
        tests.append(True)
    else:
        print("   ❌ Desktop sidebar should have flex-shrink: 0")
        tests.append(False)

    # Test 3: Desktop sidebar should have height: 100vh
    print("\n3. Testing desktop sidebar height...")
    height_pattern = r'\.friday-sidebar\s*\{[^}]*height:\s*100vh[^}]*\}'
    if re.search(height_pattern, content, re.DOTALL):
        print("   ✅ Desktop sidebar has height: 100vh")
        tests.append(True)
    else:
        print("   ❌ Desktop sidebar should have height: 100vh")
        tests.append(False)

    # Test 4: Tablet breakpoint should have margin-left on main
    print("\n4. Testing tablet breakpoint...")
    # Check if tablet media query exists and contains margin-left for friday-main
    tablet_section = re.search(r'@media\s*\(max-width:\s*992px\).*?(?=@media|$)', content, re.DOTALL)
    if tablet_section and 'margin-left: var(--sidebar-width-collapsed)' in tablet_section.group(0):
        print("   ✅ Tablet main has margin-left: var(--sidebar-width-collapsed)")
        tests.append(True)
    else:
        print("   ❌ Tablet main should have margin-left: var(--sidebar-width-collapsed)")
        tests.append(False)

    # Test 5: Mobile sidebar should use transform: translateX(-100%)
    print("\n5. Testing mobile sidebar positioning...")
    mobile_pattern = r'@media\s*\(max-width:\s*768px\)[^}]*\.friday-sidebar\s*\{[^}]*transform:\s*translateX\(-100%\)[^}]*\}'
    if re.search(mobile_pattern, content, re.DOTALL):
        print("   ✅ Mobile sidebar uses transform: translateX(-100%)")
        tests.append(True)
    else:
        print("   ❌ Mobile sidebar should use transform: translateX(-100%)")
        tests.append(False)

    # Test 6: Mobile main should have margin-left: 0
    print("\n6. Testing mobile main spacing...")
    # Check if mobile media query exists and contains margin-left: 0 for friday-main
    mobile_section = re.search(r'@media\s*\(max-width:\s*768px\).*?(?=@media|/\*|$)', content, re.DOTALL)
    if mobile_section and 'margin-left: 0' in mobile_section.group(0):
        print("   ✅ Mobile main has margin-left: 0")
        tests.append(True)
    else:
        print("   ❌ Mobile main should have margin-left: 0")
        tests.append(False)

    # Test 7: Transition timing should be 0.22s
    print("\n7. Testing transition timing...")
    transition_var = r'--sidebar-transition:[^;]*0\.22s'
    if re.search(transition_var, content):
        print("   ✅ Transition timing is 0.22s")
        tests.append(True)
    else:
        print("   ❌ Transition timing should be 0.22s")
        tests.append(False)

    # Summary
    print("\n" + "="*60)
    passed = sum(tests)
    total = len(tests)

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nCSS changes are correctly implemented!")
        print("\nManual Testing Required:")
        print("1. Open the application in a browser")
        print("2. Desktop (>992px): Toggle sidebar - main should expand/contract")
        print("3. Tablet (768-992px): Resize - sidebar fixed, main has margin")
        print("4. Mobile (<768px): Resize - sidebar off-screen, main full width")
        print("5. Verify smooth 0.22s transitions")
        print("6. Verify no horizontal scroll")
        return True
    else:
        print(f"❌ TESTS FAILED ({passed}/{total} passed)")
        return False

def verify_html_structure():
    """Verify that base.html has correct structure"""
    print("\n" + "="*60)
    print("HTML Structure Verification")
    print("="*60)

    base_html = 'templates/base.html'

    if not os.path.exists(base_html):
        print(f"❌ ERROR: {base_html} not found")
        return False

    with open(base_html, 'r') as f:
        content = f.read()

    # Check for correct structure
    print("\n1. Checking for .friday-layout container...")
    if '<div class="friday-layout">' in content:
        print("   ✅ .friday-layout container found")
    else:
        print("   ❌ .friday-layout container not found")
        return False

    print("\n2. Checking sidebar inclusion...")
    if "{% include 'partials/sidebar.html' %}" in content:
        print("   ✅ Sidebar included correctly")
    else:
        print("   ❌ Sidebar inclusion not found")
        return False

    print("\n3. Checking .friday-main container...")
    if '<div class="friday-main">' in content:
        print("   ✅ .friday-main container found")
    else:
        print("   ❌ .friday-main container not found")
        return False

    print("\n4. Checking structure order...")
    layout_pos = content.find('<div class="friday-layout">')
    sidebar_pos = content.find("{% include 'partials/sidebar.html' %}")
    main_pos = content.find('<div class="friday-main">')

    if layout_pos < sidebar_pos < main_pos:
        print("   ✅ Structure order is correct (layout → sidebar → main)")
    else:
        print("   ❌ Structure order is incorrect")
        return False

    print("\n✅ HTML structure is correct!")
    return True

if __name__ == '__main__':
    print("\n" + "="*60)
    print("ISSUE-54: Sidebar Overlap Fix - Verification Script")
    print("="*60)

    css_ok = verify_css_changes()
    html_ok = verify_html_structure()

    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)

    if css_ok and html_ok:
        print("\n✅ All automated checks passed!")
        print("\nThe sidebar overlap issue has been fixed:")
        print("• Desktop: position: relative with flex-shrink: 0")
        print("• Tablet: position: fixed with margin-left on main")
        print("• Mobile: position: fixed with translateX(-100%)")
        print("\nHTML structure is correct - sidebar and main are direct")
        print("children of .friday-layout container.")
        print("\nNext step: Manual browser testing across all breakpoints")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Review the output above.")
        sys.exit(1)
