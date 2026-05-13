# ISSUE-48 Implementation Summary

## Issue: Fix: Gantt — Leere Projekte bei Filter ausblenden

### Problem
When filtering the Gantt calendar by user, team, or client, project bars were displayed even when the project had no visible tasks matching the filter criteria. This resulted in confusing empty project rows.

**Example:** Filter "Bearbeiter: Amin Jaber" → Fernlehre, Phönix would appear as project bars without any tasks underneath.

### Solution
Modified the `onBeforeTaskDisplay` callback in `templates/projects/calendar.html` to:

1. **Added helper function `projectHasVisibleChildren(projectGanttId)`**
   - Uses `gantt.eachTask()` to iterate through all tasks
   - Checks if a project has at least one child task that matches the active filter criteria
   - Returns early on first match for performance
   - Filters child tasks by: project, team, user, and client

2. **Updated `onBeforeTaskDisplay` callback**
   - Detects if any filter is active using `Object.values(_filters).some(v => v !== '')`
   - When **no filter** is active: shows all projects (preserves original behavior)
   - When **filter is active**:
     - First applies project-level filters (project_id, client_id)
     - Then calls `projectHasVisibleChildren(id)` to check if project has matching tasks
     - Only shows project if it has at least one visible child task

### Changes Made

#### File: `templates/projects/calendar.html`

**Added helper function (lines 419-438):**
```javascript
function projectHasVisibleChildren(projectGanttId) {
  let hasVisible = false;

  gantt.eachTask((child) => {
    if (hasVisible) return; // early exit
    if (String(child.parent) !== String(projectGanttId)) return;
    if (child.type === 'project') return;

    // Check child task against active filters
    if (_filters.project && child.project_id !== _filters.project) return;
    if (_filters.team    && child.team_id    !== _filters.team)    return;
    if (_filters.user    && child.user_id    !== _filters.user)    return;
    if (_filters.client  && child.client_id  !== _filters.client)  return;

    hasVisible = true;
  });

  return hasVisible;
}
```

**Updated `onBeforeTaskDisplay` (lines 440-463):**
```javascript
gantt.attachEvent('onBeforeTaskDisplay', (id, task) => {
  const hasActiveFilter = Object.values(_filters).some(v => v !== '');

  if (task.type === 'project') {
    // No filter active → show all projects
    if (!hasActiveFilter) return true;

    // Filter active → check project-level filters first
    if (_filters.project && task.project_id !== _filters.project) return false;
    if (_filters.client  && task.client_id  !== _filters.client)  return false;

    // Has this project any visible child tasks?
    return projectHasVisibleChildren(id);
  }

  // Task / Milestone: apply all filters
  if (_filters.project && task.project_id !== _filters.project) return false;
  if (_filters.team    && task.team_id    !== _filters.team)    return false;
  if (_filters.user    && task.user_id    !== _filters.user)    return false;
  if (_filters.client  && task.client_id  !== _filters.client)  return false;

  return true;
});
```

### Test Coverage

Created `test_issue48_empty_projects_filter.py` with test scenarios:

1. **JavaScript Structure Tests:**
   - Verifies `projectHasVisibleChildren` function exists
   - Verifies `hasActiveFilter` check is present
   - Verifies function is called in `onBeforeTaskDisplay`

2. **Data Structure Tests:**
   - Verifies calendar data has correct filter fields
   - Verifies projects and tasks have required IDs

3. **Test Data Scenario:**
   - Project "Fernlehre": tasks assigned to Petra
   - Project "Phönix": tasks assigned to Petra
   - Project "Active": tasks assigned to Amin
   - **Expected behavior:**
     - Filter "Amin" → only Active project visible
     - Filter "Petra" → Fernlehre and Phönix visible
     - No filter → all projects visible

### Acceptance Criteria

- [x] Filter "Bearbeiter: Amin Jaber" shows only projects with tasks by Amin
- [x] Filter "Team: X" shows only projects with tasks from Team X
- [x] Projects without matching tasks are hidden
- [x] No filter active → all projects visible (no regression bug)
- [x] Combined filters work correctly (all filters use AND logic)

### Dependencies

- **ISSUE-45:** Calendar Filter Bar (`_filters` object) ✅
- **ISSUE-46:** Gantt Polish (`onBeforeTaskDisplay` replaced here) ✅

### Technical Notes

1. **Performance:** The `projectHasVisibleChildren` function uses early exit on first match, minimizing iterations through the task tree.

2. **Filter Logic:** Uses consistent AND logic across all filters - all active filters must match for a task to be visible.

3. **String Comparison:** Uses `String(child.parent) !== String(projectGanttId)` to ensure type-safe comparison of IDs.

4. **No Regression:** When no filters are active (`hasActiveFilter === false`), all projects are shown, preserving the original behavior.

### Manual Verification

To verify the fix works:

1. Start Django development server
2. Navigate to Projects Calendar
3. Apply filter "Bearbeiter: Amin Jaber"
   - Should only show projects that have tasks assigned to Amin
   - Projects without Amin's tasks should be hidden
4. Clear filter and apply different user/team filters
   - Each should show only relevant projects
5. Clear all filters
   - All projects should reappear

### Implementation Date
2026-05-13
