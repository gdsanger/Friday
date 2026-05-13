# ISSUE-39 Implementation Summary

## Feature: Gantt — Task Duration from Story Points

**Issue:** [ISSUE-39](https://github.com/gdsanger/Friday/issues/39)
**Branch:** `claude/issue-39-gantt-task-duration`
**Status:** ✅ Implemented and Tested

---

## Overview

Tasks with `deadline` and `story_points` are now rendered in the Gantt chart as bars with actual duration, calculated backwards from the deadline. Tasks without story points continue to render as milestone points.

```
Before:  ◆ Task (Milestone point)
After:   [════════ Task ════════◆] (Bar with start_date + deadline)
```

### Calculation Logic

- **1 SP = 1 hour**
- **8 SP = 1 working day**
- `start_date` = `deadline` minus X working days (backwards)
- Weekends (Saturday/Sunday) are skipped
- Minimum: 1 working day (even for < 8 SP)

### Examples

```python
deadline = Friday 2026-06-20
story_points = 16 SP = 2 working days
→ start_date = Wednesday 2026-06-18

deadline = Monday 2026-06-22
story_points = 8 SP = 1 working day
→ start_date = Friday 2026-06-19 (weekend skipped)
```

---

## Changes Made

### 1. Utility Functions (`apps/projects/utils.py`)

New file with two helper functions:

#### `subtract_working_days(end_date: date, working_days: int) -> date`
- Subtracts working days from a date
- Skips weekends (Saturday=5, Sunday=6)
- Returns the calculated start date

#### `sp_to_working_days(story_points: float) -> int`
- Converts story points to working days
- Uses `Decimal` with `ROUND_HALF_UP` for proper rounding
- Formula: `days = story_points / 8`
- Minimum: 1 working day

**Test Coverage:** 9 unit tests in `apps/projects/tests.py`

---

### 2. Backend (`apps/projects/views.py`)

Updated `CalendarDataView.get()` to calculate task duration:

```python
from apps.projects.utils import subtract_working_days, sp_to_working_days

# Inside task loop:
if task.story_points and task.story_points > 0:
    working_days = sp_to_working_days(float(task.story_points))
    start_date = subtract_working_days(end_date, working_days)
    duration = None  # calculated from start/end by DHTMLX
    task_type = 'task'  # renders as bar
else:
    start_date = end_date  # milestone: start = end
    duration = 0  # renders as point
    task_type = 'milestone'
```

**New task data fields:**
- `start_date`: Calculated start date (string 'YYYY-MM-DD')
- `end_date`: Deadline (string 'YYYY-MM-DD')
- `type`: 'task' or 'milestone'
- `story_points`: Float or None
- `working_days`: Integer (days calculated from SP)
- `priority_label`: Human-readable priority
- `status_label`: Human-readable status
- `color`: Project color (for bar styling)

**Test Coverage:** 6 integration tests in `apps/projects/test_issue39_gantt_duration.py`

---

### 3. Frontend (`templates/projects/calendar.html`)

#### New SP Column in Grid

```javascript
{
  name: "sp", label: "SP",
  align: "center", width: 45,
  template: (task) => task.story_points
    ? `<span style="font-family:monospace;font-size:12px">${task.story_points}</span>`
    : ''
}
```

#### Enhanced Tooltips

```javascript
gantt.plugins({ tooltip: true });

gantt.templates.tooltip_text = (start, end, task) => {
  if (task.type === 'milestone') {
    return `<b>${task.text}</b><br>Deadline: ${fmtDate(task.start_date)}`;
  }
  const sp = task.story_points ? `${task.story_points} SP` : '—';
  const days = task.working_days ? `${task.working_days} AT` : '—';
  return `
    <b>${task.text}</b><br>
    Start: ${fmtDate(task.start_date)}<br>
    Deadline: ${fmtDate(task.end_date)}<br>
    Aufwand: ${sp} (${days})<br>
    Status: ${task.status_label || '—'}<br>
    ${task.resource_label ? `Bearbeiter: ${task.resource_label}` : ''}
  `.trim();
};
```

#### Status-Based Task Coloring

```javascript
gantt.templates.task_style = (start, end, task) => {
  // Project bars: use project color
  if (task.type === 'project') {
    return task.color
      ? `background:${task.color}; border-color:${task.color};`
      : '';
  }

  // Task bars: use status color
  const statusColors = {
    'backlog':     '#6b7280',  // gray
    'todo':        '#3b82f6',  // blue
    'in_progress': '#f59e0b',  // amber
    'review':      '#8b5cf6',  // purple
    'done':        '#10b981',  // green
  };
  const color = statusColors[task.status] || task.color || '#3b82f6';
  return `background:${color}; border-color:${color};`;
};
```

#### Weekend Highlighting

```javascript
// Mark weekend columns
gantt.templates.scale_cell_class = (date) => {
  if (date.getDay() === 0 || date.getDay() === 6) {
    return 'weekend-cell';
  }
  return '';
};

gantt.templates.timeline_cell_class = (task, date) => {
  if (date.getDay() === 0 || date.getDay() === 6) {
    return 'weekend-cell';
  }
  return '';
};
```

**CSS:**
```css
.weekend-cell {
  background: rgba(107, 114, 128, 0.08) !important;
}
[data-bs-theme="dark"] .weekend-cell {
  background: rgba(255, 255, 255, 0.03) !important;
}
```

#### Improved Text Templates

```javascript
{
  name: "text", label: "Project / Task",
  tree: true, width: 220,
  template: (task) => task.type === 'milestone'
    ? `<span style="padding-left:16px;font-size:12px;opacity:.7">${task.text}</span>`
    : task.type === 'project'
      ? `<span style="font-weight:600">${task.text}</span>`
      : `<span style="padding-left:16px;font-size:13px">${task.text}</span>`
}
```

---

## Testing

### Unit Tests (`apps/projects/tests.py`) - 9 tests
- ✅ `subtract_working_days(Mon, 1)` → Friday (skip weekend)
- ✅ `subtract_working_days(Fri, 2)` → Wednesday
- ✅ `subtract_working_days(date, 0)` → same date
- ✅ `subtract_working_days(date, -5)` → same date
- ✅ `sp_to_working_days(8)` → 1
- ✅ `sp_to_working_days(16)` → 2
- ✅ `sp_to_working_days(4)` → 1 (minimum)
- ✅ `sp_to_working_days(20)` → 3 (rounded up)
- ✅ `sp_to_working_days(1)` → 1 (minimum)

### Integration Tests (`apps/projects/test_issue39_gantt_duration.py`) - 6 tests
- ✅ Task with SP renders as bar with correct dates
- ✅ Task without SP renders as milestone
- ✅ Weekend skipping works correctly (Mon deadline - 1 day = Fri)
- ✅ Status/priority labels included in data
- ✅ Tasks without deadline excluded from Gantt
- ✅ Resource assignment works correctly

**All 15 tests pass ✓**

---

## Acceptance Criteria Status

### Berechnung
- ✅ `subtract_working_days(date(2026,6,22), 1)` → `date(2026,6,19)` (Montag-1AT=Freitag)
- ✅ `subtract_working_days(date(2026,6,20), 2)` → `date(2026,6,18)` (Fr-2AT=Mi)
- ✅ `sp_to_working_days(8)` → `1`
- ✅ `sp_to_working_days(16)` → `2`
- ✅ `sp_to_working_days(4)` → `1` (Minimum 1 Arbeitstag)
- ✅ `sp_to_working_days(20)` → `3` (gerundet)

### Gantt-Darstellung
- ✅ Tasks mit `deadline` + `story_points` → Balken mit Start- und Enddatum
- ✅ Tasks mit `deadline` ohne `story_points` → Milestone (Raute/Punkt)
- ✅ Tasks ohne `deadline` → nicht im Gantt
- ✅ Balken endet immer am `deadline`-Datum
- ✅ Balken startet X Arbeitstage vor der Deadline (Wochenenden übersprungen)
- ✅ Balkenfarbe zeigt den Task-Status (grau/blau/gelb/lila/grün)
- ✅ Projektbalken behalten Projektfarbe
- ✅ SP-Spalte im Grid zeigt Story Points wenn vorhanden

### Tooltip
- ✅ Hover auf Task-Balken zeigt: Titel, Start, Deadline, SP, Arbeitstage, Status, Bearbeiter
- ✅ Hover auf Milestone zeigt: Titel, Deadline

### Wochenenden
- ✅ Sa/So Spalten sind visuell ausgegraut im Gantt
- ✅ Funktioniert in Light und Dark Mode

---

## Files Modified

1. **`apps/projects/utils.py`** (NEW)
   - Utility functions for working day calculations

2. **`apps/projects/views.py`**
   - Updated `CalendarDataView` to calculate task durations

3. **`templates/projects/calendar.html`**
   - Added SP column, tooltips, status colors, weekend highlighting

4. **`apps/projects/tests.py`** (NEW)
   - Unit tests for utility functions

5. **`apps/projects/test_issue39_gantt_duration.py`** (NEW)
   - Integration tests for CalendarDataView

---

## Dependencies

This feature builds on:
- **ISSUE-24** — Gantt View + CalendarDataView
- **ISSUE-26** — Gantt Script/Date Fix
- **ISSUE-33** — Story Points on Task (`task.story_points` field)

---

## Usage Example

### Creating a Task with Story Points

```python
task = Task.objects.create(
    title='Implement API endpoint',
    project=my_project,
    deadline=date(2026, 6, 20),  # Friday
    story_points=16,  # 2 working days
    status='todo'
)
```

### Gantt Display

This task will render in the Gantt chart as:
- **Bar** (not a milestone point)
- **Start Date:** Wednesday 2026-06-18
- **End Date:** Friday 2026-06-20
- **Color:** Blue (todo status)
- **Tooltip:** Shows "16 SP (2 AT)"

### Viewing in Calendar

Navigate to `/projects/calendar/` to see the Gantt chart with all tasks displayed according to their story points and deadlines.

---

## Notes

- Story points are stored as `DecimalField` with precision (5, 1)
- The feature gracefully handles tasks without story points (renders as milestones)
- Weekend skipping uses Python's `date.weekday()` (0=Monday, 6=Sunday)
- Rounding uses `Decimal.ROUND_HALF_UP` to ensure 2.5 rounds to 3
- All date strings are in ISO 8601 format ('YYYY-MM-DD') for DHTMLX Gantt compatibility

---

## Future Enhancements

Potential improvements for future iterations:

1. **Holiday Calendar:** Integrate with a holiday calendar to skip public holidays
2. **Custom Work Hours:** Support different work hour definitions (e.g., 6h/day instead of 8h)
3. **Team Capacity:** Show team capacity vs planned work in tooltips
4. **Drag & Drop:** Allow dragging task bars to adjust deadlines or story points
5. **Auto-scheduling:** Automatically schedule tasks based on dependencies and capacity

---

**Implementation Date:** 2026-05-13
**Tests:** 15/15 passing ✓
**Status:** Ready for review and deployment
