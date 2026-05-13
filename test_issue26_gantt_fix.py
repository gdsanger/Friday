#!/usr/bin/env python
"""
Test script to verify ISSUE-26 fix: Gantt Script Loading Order & date.match Error

This script verifies that:
1. The calendar template loads dhtmlxgantt.js before any gantt configuration
2. Column templates use fmtDate() helper instead of gantt.date.str_to_date() at definition time
3. Date normalization is in place before gantt.parse()
4. gantt.config.xml_date is set for extra safety
5. baseColumns snapshot is saved before toggle modifies columns
6. gantt.init() is called after all config, before addMarker()
"""

import os
import re

def test_template_structure():
    """Verify the template has the correct structure"""
    print("\n── Test 1: Template Structure ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Find the extra_js block
    extra_js_match = re.search(r'{% block extra_js %}(.*?){% endblock %}', content, re.DOTALL)
    assert extra_js_match, "Should have extra_js block"
    extra_js = extra_js_match.group(1)

    # 1. Check dhtmlxgantt.js is loaded first (before any gantt.* calls)
    script_load_pos = extra_js.find('dhtmlxgantt.js')
    first_gantt_config = extra_js.find('gantt.config')
    assert script_load_pos > 0, "Should load dhtmlxgantt.js"
    assert script_load_pos < first_gantt_config, "dhtmlxgantt.js should load before gantt.config"
    print("  ✓ dhtmlxgantt.js loads before gantt configuration")

    # 2. Check gantt.config.xml_date is set
    assert 'gantt.config.xml_date' in extra_js, "Should set gantt.config.xml_date"
    assert '"%Y-%m-%d"' in extra_js, "xml_date should be set to %Y-%m-%d"
    print("  ✓ gantt.config.xml_date is set for extra safety")

    # 3. Check fmtDate() helper function exists
    assert 'function fmtDate(' in extra_js, "Should have fmtDate() helper function"
    print("  ✓ fmtDate() helper function is defined")

    # 4. Check column templates use fmtDate() instead of gantt.date.str_to_date()
    assert 'fmtDate(task.start_date)' in extra_js, "Should use fmtDate() for start_date"
    assert 'fmtDate(task.end_date)' in extra_js, "Should use fmtDate() for end_date"
    assert 'gantt.date.str_to_date' not in extra_js or extra_js.count('gantt.date.str_to_date') == 0 or \
           (extra_js.find('gantt.date.str_to_date') > extra_js.find('gantt.init')), \
           "Column templates should not use gantt.date.str_to_date() at definition time"
    print("  ✓ Column templates use fmtDate() instead of gantt.date.str_to_date()")

    # 5. Check date normalization before gantt.parse()
    assert 'const normalize = (dateVal)' in extra_js, "Should have normalize function"
    assert 'String(dateVal).split' in extra_js, "Should normalize dates to strings"
    normalize_pos = extra_js.find('const normalize')
    parse_pos = extra_js.find('gantt.parse')
    assert normalize_pos < parse_pos, "normalize should be defined before gantt.parse()"
    print("  ✓ Date normalization is in place before gantt.parse()")

    # 6. Check baseColumns snapshot is saved
    assert 'const baseColumns = [...gantt.config.columns]' in extra_js, \
           "Should save baseColumns snapshot"
    basecolumns_pos = extra_js.find('const baseColumns')
    toggle_func_pos = extra_js.find('function toggleResourceView()')
    assert basecolumns_pos < toggle_func_pos, \
           "baseColumns should be defined before toggleResourceView()"
    print("  ✓ baseColumns snapshot is saved before toggle modifies columns")

    # 7. Check gantt.init() is after all config but before addMarker()
    init_pos = extra_js.find('gantt.init("gantt-container")')
    addmarker_pos = extra_js.find('gantt.addMarker(')
    scales_pos = extra_js.find('gantt.config.scales')
    columns_pos = extra_js.find('gantt.config.columns')

    assert init_pos > columns_pos, "gantt.init() should be after columns config"
    assert init_pos > scales_pos, "gantt.init() should be after scales config"
    assert init_pos < addmarker_pos, "gantt.init() should be before addMarker()"
    print("  ✓ gantt.init() is called after all config, before addMarker()")

    print("  ✅ PASSED: Template structure is correct")


def test_no_definition_time_gantt_calls():
    """Verify that gantt.date.* is not called at column definition time"""
    print("\n── Test 2: No Definition-Time gantt.date.* Calls ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Find the columns definition
    columns_match = re.search(r'gantt\.config\.columns = \[(.*?)\];', content, re.DOTALL)
    assert columns_match, "Should have columns definition"
    columns_section = columns_match.group(1)

    # Check that gantt.date.str_to_date() is NOT in the columns section
    assert 'gantt.date.str_to_date' not in columns_section, \
           "Column templates should not call gantt.date.str_to_date() at definition time"

    # Check that fmtDate() or fmtShort() is used instead
    assert 'fmtDate(' in columns_section or 'fmtShort(' in columns_section, \
           "Column templates should use fmtDate() or fmtShort() helper"

    print("  ✓ Column templates do not call gantt.date.* at definition time")
    print("  ✓ Column templates use fmtDate()/fmtShort() helper which is called at render time")
    print("  ✅ PASSED: No definition-time gantt.date.* calls")


def test_date_format_helper():
    """Verify the fmtDate helper formats dates correctly"""
    print("\n── Test 3: Date Format Helper Logic ──")

    template_path = '/home/runner/work/Friday/Friday/templates/projects/calendar.html'

    with open(template_path, 'r') as f:
        content = f.read()

    # Check fmtDate implementation
    fmtdate_match = re.search(r'function fmtDate\(.*?\)(.*?)^}', content, re.MULTILINE | re.DOTALL)
    assert fmtdate_match, "Should have fmtDate function"
    fmtdate_code = fmtdate_match.group(0)

    # Verify it handles empty values
    assert 'if (!dateStr) return' in fmtdate_code, "Should handle empty dates"

    # Verify it uses String().split() for string manipulation
    assert 'String(dateStr).split' in fmtdate_code, "Should use String.split() for parsing"

    # Verify it splits on 'T' to handle ISO datetime strings
    assert "split('T')[0]" in fmtdate_code, "Should split on 'T' to handle ISO datetime"

    # Verify it formats as dd.mm.YYYY
    assert 'parts[2]' in fmtdate_code and 'parts[1]' in fmtdate_code and 'parts[0]' in fmtdate_code, \
           "Should reorder date parts for German format"

    print("  ✓ fmtDate() handles empty dates")
    print("  ✓ fmtDate() uses String.split() for safe parsing")
    print("  ✓ fmtDate() splits on 'T' to handle ISO datetime")
    print("  ✓ fmtDate() formats as dd.mm.YYYY")
    print("  ✅ PASSED: Date format helper is correct")


def run_all_tests():
    """Run all acceptance criteria tests"""
    print("=" * 60)
    print("ISSUE-26: Fix Gantt Script Loading Order & date.match Error")
    print("Acceptance Criteria Tests")
    print("=" * 60)

    try:
        test_template_structure()
        test_no_definition_time_gantt_calls()
        test_date_format_helper()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe fix successfully addresses the date.match error by:")
        print("  1. Loading dhtmlxgantt.js before any gantt configuration")
        print("  2. Using fmtDate() helper called at render time, not definition time")
        print("  3. Normalizing dates to plain strings before gantt.parse()")
        print("  4. Setting gantt.config.xml_date for extra safety")
        print("  5. Saving baseColumns snapshot before toggle modifies columns")
        print("  6. Calling gantt.init() after all config, before addMarker()")
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
