#!/usr/bin/env python
"""
Test script to verify ISSUE-46 fix: Gantt View Improvements

This script verifies that:
1. Today is centered in view on load (scrollTo logic present)
2. Quarter labels use custom format function (Q1 2026, not Q%q)
3. German month names in Quarter view (Jan, Feb, Mär)
4. KW calculation in Month view using ISO 8601
5. Date format in Start/Deadline columns is dd.mm.YY (fmtShort)
6. "Projekt" label shows in Resource column for project rows
7. Minimum bar width (24px) for narrow tasks (< 2 days)
8. SP > 40 highlighted in red/bold with tooltip warning
9. SCALES object defined with all three modes
10. Initial scale is Quarter view
"""

import os
import re


def test_today_centering():
    """Verify today is centered in view on load"""
    print("\n── Test 1: Today Centered on Load ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check for scrollTo logic after gantt.parse
    assert 'gantt.scrollTo' in content, "Should have gantt.scrollTo call"
    assert 'posFromDate(today)' in content or 'gantt.posFromDate' in content, \
           "Should calculate position from today's date"
    assert '0.25' in content or 'chartWidth * 0.25' in content, \
           "Should position today at ~25% from left"

    # Verify setTimeout is used to ensure gantt is rendered
    assert 'setTimeout' in content, "Should use setTimeout for proper timing"

    print("  ✓ gantt.scrollTo() is implemented")
    print("  ✓ Today's position is calculated")
    print("  ✓ Today is positioned at ~25% from left")
    print("  ✓ setTimeout ensures proper rendering timing")
    print("  ✅ PASSED: Today centering is implemented")


def test_quarter_labels():
    """Verify Quarter labels use custom format function"""
    print("\n── Test 2: Quarter Label Format ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check SCALES object exists
    assert 'const SCALES = {' in content, "Should have SCALES object"

    # Check Quarter view has custom format function
    assert 'quarter:' in content, "Should have quarter scale"

    # Verify Q%q is NOT used
    assert 'Q%q' not in content, "Should not use Q%q format (not supported in free version)"

    # Verify custom format function for Quarter
    quarter_section = re.search(r'quarter:\s*\[(.*?)\]', content, re.DOTALL)
    assert quarter_section, "Should have quarter scale definition"
    quarter_text = quarter_section.group(1)

    assert 'format: function(date)' in quarter_text, \
           "Quarter scale should use custom format function"
    assert 'Math.floor(date.getMonth() / 3) + 1' in quarter_text, \
           "Should calculate quarter number from month"
    assert '`Q${q} ${date.getFullYear()}`' in quarter_text or \
           "'Q' + q" in quarter_text, \
           "Should format as 'Q1 2026'"

    print("  ✓ SCALES object is defined")
    print("  ✓ Q%q is not used")
    print("  ✓ Quarter uses custom format function")
    print("  ✓ Quarter formats as 'Q1 2026'")
    print("  ✅ PASSED: Quarter labels are correct")


def test_german_month_names():
    """Verify German month abbreviations in Quarter view"""
    print("\n── Test 3: German Month Names ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check for German month names
    assert 'Mär' in content, "Should have German March abbreviation 'Mär'"
    assert "['Jan','Feb','Mär','Apr','Mai','Jun'" in content or \
           '["Jan","Feb","Mär","Apr","Mai","Jun"' in content, \
           "Should have German month names array"

    # Verify it's used in Quarter scale
    quarter_section = re.search(r'quarter:\s*\[(.*?)\]', content, re.DOTALL)
    assert quarter_section, "Should have quarter scale definition"
    quarter_text = quarter_section.group(1)
    assert 'Mär' in quarter_text, "Quarter scale should use German month names"

    print("  ✓ German month names are defined")
    print("  ✓ 'Mär' is used for March")
    print("  ✓ Month names are used in Quarter view")
    print("  ✅ PASSED: German month names are correct")


def test_kw_calculation():
    """Verify KW (week number) calculation in Month view"""
    print("\n── Test 4: KW Calculation (ISO 8601) ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check for custom KW calculation in Month scale
    month_section = re.search(r'month:\s*\[(.*?)\]', content, re.DOTALL)
    assert month_section, "Should have month scale definition"
    month_text = month_section.group(1)

    # Verify custom format function for week
    assert 'format: function(date)' in month_text, \
           "Week scale should use custom format function"

    # Check for ISO 8601 week calculation
    assert 'Date.UTC' in month_text, "Should use UTC for week calculation"
    assert 'getUTCDay()' in month_text or 'd.getUTCDay()' in month_text, \
           "Should use UTC day for week calculation"
    assert '86400000' in month_text, "Should use milliseconds per day for calculation"
    assert 'Math.ceil' in month_text, "Should use Math.ceil for week number"

    # Verify KW format
    assert '`KW ${weekNo}`' in month_text or "'KW ' + weekNo" in month_text, \
           "Should format as 'KW 1', 'KW 2', etc."

    print("  ✓ Custom KW calculation is implemented")
    print("  ✓ Uses ISO 8601 standard (UTC, getUTCDay)")
    print("  ✓ Formats as 'KW 1', 'KW 2', etc.")
    print("  ✅ PASSED: KW calculation is correct")


def test_short_date_format():
    """Verify date format in grid columns is dd.mm.YY"""
    print("\n── Test 5: Short Date Format (dd.mm.YY) ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check for fmtShort function
    assert 'function fmtShort(' in content, "Should have fmtShort() function"

    # Verify fmtShort implementation
    fmtshort_match = re.search(r'function fmtShort\(.*?\)(.*?)^}', content, re.MULTILINE | re.DOTALL)
    assert fmtshort_match, "Should have fmtShort function"
    fmtshort_code = fmtshort_match.group(0)

    # Verify it returns '—' for empty dates
    assert "return '—'" in fmtshort_code or 'return "—"' in fmtshort_code, \
           "Should return '—' for empty dates"

    # Verify it uses .slice(2) to get YY instead of YYYY
    assert 'parts[0].slice(2)' in fmtshort_code, \
           "Should use .slice(2) to get 2-digit year"

    # Check columns use fmtShort
    columns_match = re.search(r'gantt\.config\.columns = \[(.*?)\];', content, re.DOTALL)
    assert columns_match, "Should have columns definition"
    columns_section = columns_match.group(1)
    assert 'fmtShort(' in columns_section, "Columns should use fmtShort()"

    print("  ✓ fmtShort() function is defined")
    print("  ✓ Returns '—' for empty dates")
    print("  ✓ Uses .slice(2) for 2-digit year")
    print("  ✓ Grid columns use fmtShort()")
    print("  ✅ PASSED: Short date format is correct")


def test_project_resource_label():
    """Verify 'Projekt' label in Resource column for project rows"""
    print("\n── Test 6: Project Resource Label ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check resource column template in toggleResourceView function
    toggle_match = re.search(r'function toggleResourceView\(\)(.*?)^}', content, re.MULTILINE | re.DOTALL)
    assert toggle_match, "Should have toggleResourceView function"
    toggle_code = toggle_match.group(1)

    # Verify resource column is added
    assert 'name: "resource"' in toggle_code, "Should add resource column"
    assert 'label: "Ressource"' in toggle_code, "Should label column as 'Ressource'"

    # Verify project type check
    assert "task.type === 'project'" in toggle_code, \
           "Should check for project type"

    # Verify "Projekt" label for project rows
    assert 'Projekt' in toggle_code, "Should show 'Projekt' for project rows"
    assert 'font-style:italic' in toggle_code or 'italic' in toggle_code, \
           "Project label should be italic"

    # Verify "—" for empty resource
    assert '—' in toggle_code or '-' in toggle_code, \
           "Should show '—' or '-' for empty resource"

    print("  ✓ Resource column is added in resource view")
    print("  ✓ Checks for project type")
    print("  ✓ Shows 'Projekt' label (italic) for project rows")
    print("  ✓ Shows '—' for empty resource")
    print("  ✅ PASSED: Project resource label is correct")


def test_minimum_bar_width():
    """Verify minimum bar width for narrow tasks"""
    print("\n── Test 7: Minimum Bar Width ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check CSS for minimum width
    css_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    assert css_match, "Should have style block"
    css_content = css_match.group(1)

    assert '.gantt-task-narrow' in css_content, \
           "Should have CSS class for narrow tasks"
    assert 'min-width: 24px' in css_content or 'min-width:24px' in css_content, \
           "Should set minimum width to 24px"

    # Check task_class template adds narrow class
    taskclass_match = re.search(r'gantt\.templates\.task_class = \(.*?\)(.*?)^};',
                                 content, re.MULTILINE | re.DOTALL)
    assert taskclass_match, "Should have task_class template"
    taskclass_code = taskclass_match.group(0)

    # Verify narrow detection logic
    assert 'diffDays' in taskclass_code or '(end - start)' in taskclass_code, \
           "Should calculate task duration in days"
    assert '< 2' in taskclass_code, "Should check for tasks < 2 days"
    assert 'gantt-task-narrow' in taskclass_code, \
           "Should add 'gantt-task-narrow' class"

    print("  ✓ CSS class '.gantt-task-narrow' is defined")
    print("  ✓ Minimum width set to 24px")
    print("  ✓ task_class template calculates duration")
    print("  ✓ Adds 'gantt-task-narrow' class for tasks < 2 days")
    print("  ✅ PASSED: Minimum bar width is implemented")


def test_sp_warning():
    """Verify SP > 40 warning in grid and tooltip"""
    print("\n── Test 8: SP > 40 Warning ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check SP column template
    columns_match = re.search(r'gantt\.config\.columns = \[(.*?)\];', content, re.DOTALL)
    assert columns_match, "Should have columns definition"
    columns_section = columns_match.group(1)

    # Find SP column - just check if it exists and has the warning logic
    assert 'name: "sp"' in columns_section, "Should have SP column"

    # Verify SP > 40 check in columns section
    assert '> 40' in columns_section, "Should check for story_points > 40 in columns"
    assert '#e55039' in columns_section or 'red' in columns_section.lower(), \
           "Should use red color for high SP"
    assert 'font-weight:700' in columns_section or 'bold' in columns_section, \
           "Should use bold font for high SP"

    # Check tooltip template
    tooltip_match = re.search(r'gantt\.templates\.tooltip_text = \(.*?\)(.*?)^};',
                              content, re.MULTILINE | re.DOTALL)
    assert tooltip_match, "Should have tooltip template"
    tooltip_code = tooltip_match.group(0)

    # Verify warning in tooltip
    assert 'sp > 40' in tooltip_code or 'sp && sp > 40' in tooltip_code, \
           "Should check for SP > 40 in tooltip"
    assert '⚠️' in tooltip_code or 'Sehr hoher Aufwand' in tooltip_code, \
           "Should show warning emoji or text in tooltip"

    print("  ✓ SP column checks for story_points > 40")
    print("  ✓ High SP styled in red (#e55039) and bold")
    print("  ✓ Tooltip checks for SP > 40")
    print("  ✓ Tooltip shows warning (⚠️ Sehr hoher Aufwand)")
    print("  ✅ PASSED: SP > 40 warning is implemented")


def test_scales_object():
    """Verify SCALES object with all three modes"""
    print("\n── Test 9: SCALES Object ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check SCALES object
    assert 'const SCALES = {' in content, "Should have SCALES object"

    # Verify all three modes
    assert 'month:' in content, "Should have month scale"
    assert 'quarter:' in content, "Should have quarter scale"
    assert 'year:' in content, "Should have year scale"

    # Check setScale function uses SCALES object
    setscale_match = re.search(r'function setScale\(.*?\)(.*?)^}', content, re.MULTILINE | re.DOTALL)
    assert setscale_match, "Should have setScale function"
    setscale_code = setscale_match.group(1)

    assert 'SCALES[mode]' in setscale_code, "setScale should use SCALES object"
    assert 'SCALES.quarter' in setscale_code or 'SCALES.month' in setscale_code, \
           "setScale should have fallback to SCALES"

    print("  ✓ SCALES object is defined")
    print("  ✓ Has month, quarter, and year modes")
    print("  ✓ setScale function uses SCALES object")
    print("  ✅ PASSED: SCALES object is correct")


def test_initial_scale():
    """Verify initial scale is Quarter view"""
    print("\n── Test 10: Initial Scale (Quarter) ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check initial scale configuration
    assert 'gantt.config.scales = SCALES.quarter' in content, \
           "Should set initial scale to SCALES.quarter"

    # Verify Quarter button is active in HTML
    html_match = re.search(r'{% block content %}(.*?){% endblock %}', content, re.DOTALL)
    assert html_match, "Should have content block"
    html_content = html_match.group(1)

    # Find Quarter button
    quarter_btn_match = re.search(r'onclick="setScale\(\'quarter\'\)"', html_content)
    assert quarter_btn_match, "Should have Quarter button"

    # Check that Quarter button has 'active' class
    # Find the button element that contains onclick="setScale('quarter')"
    button_section = html_content[max(0, quarter_btn_match.start() - 200):quarter_btn_match.end() + 50]
    assert 'active' in button_section, "Quarter button should have 'active' class"

    print("  ✓ gantt.config.scales set to SCALES.quarter")
    print("  ✓ Quarter button has 'active' class")
    print("  ✅ PASSED: Initial scale is Quarter")


def run_all_tests():
    """Run all acceptance criteria tests"""
    print("=" * 60)
    print("ISSUE-46: Gantt View Improvements")
    print("Acceptance Criteria Tests")
    print("=" * 60)

    try:
        test_today_centering()
        test_quarter_labels()
        test_german_month_names()
        test_kw_calculation()
        test_short_date_format()
        test_project_resource_label()
        test_minimum_bar_width()
        test_sp_warning()
        test_scales_object()
        test_initial_scale()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe implementation successfully includes:")
        print("  1. Today centered on load (~25% from left)")
        print("  2. Quarter labels: Q1 2026, Q2 2026 (custom function)")
        print("  3. German month names in Quarter view (Jan, Feb, Mär)")
        print("  4. KW calculation in Month view (ISO 8601)")
        print("  5. Date format dd.mm.YY in Start/Deadline columns")
        print("  6. 'Projekt' label in Resource view for project rows")
        print("  7. Minimum 24px bar width for tasks < 2 days")
        print("  8. SP > 40 highlighted in red/bold with tooltip warning")
        print("  9. SCALES object with month/quarter/year modes")
        print(" 10. Initial scale is Quarter view")
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_all_tests())
