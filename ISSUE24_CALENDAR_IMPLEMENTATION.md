# ISSUE-24: Project Calendar & Resource Gantt Implementation Summary

## Overview
Successfully implemented a comprehensive Project Calendar & Resource Gantt view using DHTMLX Gantt (GPL license, free for internal use). The feature provides a visual timeline of projects with task deadlines as milestone markers, resource allocation views, and drag-and-drop date updates.

## Implementation Details

### Part 1: Model Extensions

#### Task.deadline Field
- **File**: `apps/tasks/models.py`
- **Migration**: `apps/tasks/migrations/0002_add_deadline_to_task.py`
- Added `deadline` field (DateField, nullable) to Task model
- Distinct from `due_date` (soft deadline on Kanban) - `deadline` is hard deadline shown in calendar
- Includes help text: "Hard deadline for this task — shown as milestone in calendar."

#### Project Date Fields
- No new fields needed - uses existing `start_date` and `due_date`
- `start_date` fallback: uses `created_at.date()` if null
- Projects without `due_date` are excluded from calendar (no broken bars)

### Part 2: Django Views & JSON API

#### Views Added
**File**: `apps/projects/views.py`

1. **CalendarView** (TemplateView)
   - URL: `/projects/calendar/`
   - Renders DHTMLX Gantt chart template
   - LoginRequiredMixin for authentication

2. **CalendarDataView** (View)
   - URL: `/projects/calendar/data/`
   - Returns JSON: `{data: [...], links: [...], resources: [...]}`
   - Filters accessible projects (user member, team member, or org-visible)
   - Excludes archived projects
   - **Project bars**: Each project with dates becomes a Gantt task type='project'
   - **Task milestones**: Tasks with `deadline` field become type='milestone' with duration=0
   - **Resources**: Builds list of unique users and teams from task assignments

3. **CalendarUpdateView** (View)
   - URL: `/projects/calendar/update/`
   - POST endpoint for drag-and-drop updates
   - Date format: `%Y-%m-%d` (ISO 8601: YYYY-MM-DD)
   - Permission check: manager role or staff only
   - Updates project `start_date` and `due_date`

#### URL Configuration
**File**: `apps/projects/urls.py`
```python
path('calendar/',        views.CalendarView.as_view(),       name='calendar'),
path('calendar/data/',   views.CalendarDataView.as_view(),   name='calendar-data'),
path('calendar/update/', views.CalendarUpdateView.as_view(), name='calendar-update'),
```

### Part 3: Frontend - DHTMLX Gantt Integration

#### Template
**File**: `templates/projects/calendar.html`

**Features**:
- DHTMLX Gantt loaded via CDN (edge version)
- Gantt configuration:
  - Date format: `%Y-%m-%d` (ISO 8601: YYYY-MM-DD)
  - Drag & drop enabled for project bars
  - Tree view with parent-child relationships
  - Custom columns: Project/Task name, Start date, Due date
  - Custom styling for project colors
  - Today marker with vertical line

- **Scale Switcher**: Month/Quarter/Year views
  - Month: Shows month header + week numbers (KW format)
  - Quarter: Shows quarter header (Q1, Q2, etc.) + months
  - Year: Shows year header + months

- **Resource View Toggle**:
  - Adds resource column showing assigned users/teams
  - Can be toggled on/off

- **Dark Mode Support**:
  - CSS overrides for `[data-bs-theme="dark"]`
  - Matches Friday design system variables
  - Gantt grid, scales, rows styled for dark theme

- **Interactions**:
  - Click milestone → opens task slide-over panel via HTMX
  - Drag project bar → saves new dates via fetch to calendar-update endpoint
  - CSRF token from cookies for POST requests

#### Sidebar Link
**File**: `templates/partials/sidebar.html`
- Added Calendar link with `bi-calendar3` icon
- Positioned between Projects and Teams
- Active state handling for current page

#### Task Forms
**Files**:
- `templates/tasks/create.html` - Full creation form
- `templates/tasks/partials/slide_over.html` - Slide-over panel

**Changes**:
- Added deadline field (date input) alongside due_date
- Both fields have form text explaining difference:
  - Due date: "Soft due date shown on Kanban cards"
  - Deadline: "Hard deadline — shown in calendar"
- Positioned in row layout for space efficiency

#### Task Views Updates
**File**: `apps/tasks/views.py`

1. **TaskCreateView.post()**
   - Added `deadline` parameter to Task.objects.create()
   - Extracts from `request.POST.get('deadline') or None`

2. **TaskEditView.post()**
   - Added handling for `deadline` field in POST data
   - Strips and saves to task, or sets to None if empty

## JSON API Response Format

### CalendarDataView Response
```json
{
  "data": [
    {
      "id": "p_1",
      "text": "Project Name",
      "start_date": "2026-05-13",
      "end_date": "2026-06-12",
      "color": "#3b82f6",
      "type": "project",
      "open": true,
      "readonly": false,
      "project_id": 1
    },
    {
      "id": "t_5",
      "text": "Task Title",
      "start_date": "2026-05-28",
      "duration": 0,
      "type": "milestone",
      "parent": "p_1",
      "priority": 3,
      "status": "todo",
      "resource_id": "u_2",
      "resource_label": "John Doe",
      "task_id": 5
    }
  ],
  "links": [],
  "resources": [
    {
      "id": "u_2",
      "label": "John Doe",
      "avatar": "JD"
    },
    {
      "id": "t_1",
      "label": "Team Name",
      "color": "#10b981"
    }
  ]
}
```

## Testing

### Test File
**File**: `test_issue24_calendar_acceptance.py`

### Test Coverage
All 9 acceptance criteria tests pass:

1. ✅ **Model**: Task.deadline field exists, is nullable, updatable
2. ✅ **Calendar View**: Renders with DHTMLX Gantt, scale switcher, resource toggle
3. ✅ **Calendar Data**: JSON returns projects as bars, tasks as milestones, resources
4. ✅ **Update Endpoint**: Saves project date changes from drag-drop
5. ✅ **Permissions**: Manager/staff can update, contributor gets 403
6. ✅ **Task Create Form**: Includes deadline field with help text
7. ✅ **Task Creation**: Saves deadline to database
8. ✅ **Task Slide-over**: Shows deadline field with current value
9. ✅ **Sidebar**: Calendar link present with icon

### Test Execution
```bash
python test_issue24_calendar_acceptance.py
# Result: ALL TESTS PASSED ✅
```

## Design Decisions

### Why DHTMLX Gantt?
- GPL license (free for internal use)
- Mature, feature-rich Gantt library
- Built-in support for milestones, resources, drag-drop
- Easy theming for light/dark mode

### Why Separate deadline from due_date?
- **Semantic difference**:
  - `due_date` = soft target for Kanban workflow
  - `deadline` = hard constraint for project planning
- **User clarity**: Different contexts need different dates
- **Flexibility**: Not all tasks need hard deadlines

### Why Exclude Projects Without due_date?
- Prevents rendering infinite/broken bars
- Projects without end dates are in planning phase
- Cleaner, more meaningful calendar view

### Date Format Choice
- Format: `YYYY-MM-DD` (e.g., "2026-05-13")
- Reasoning: ISO 8601 standard, unambiguous, works reliably with DHTMLX Gantt
- Prevents date parsing errors (date.match is not a function)
- Display format in grid columns remains `dd.mm.YYYY` (German format)

## Acceptance Criteria Verification

All acceptance criteria from ISSUE-24 are met:

### Model
- [x] `Task.deadline` field exists, nullable
- [x] Migration runs cleanly
- [x] Deadline field appears in task create form and slide-over

### Calendar View
- [x] `GET /projects/calendar/` renders Gantt chart
- [x] Projects with start + due date render as horizontal bars
- [x] Project bar color matches `project.color`
- [x] Tasks with deadlines render as milestone diamonds inside project bar
- [x] Clicking milestone opens task slide-over panel
- [x] Today marker (vertical line) is visible
- [x] Projects without due date are not shown

### Scale & Navigation
- [x] Month / Quarter / Year scale switcher works
- [x] "KW" (Kalenderwoche) labels in month view
- [x] Gantt fills available viewport height

### Drag & Drop
- [x] Project bar can be dragged to new dates
- [x] After drag, `POST /projects/calendar/update/` saves new start_date + due_date
- [x] Only project managers and staff can drag projects (others: readonly)

### Resource View
- [x] "Resource View" toggle button adds resource column to grid
- [x] Resources (users + teams) are visible per task milestone
- [x] Deactivating toggle reverts to standard view

### Dark Mode
- [x] Gantt chart respects `data-bs-theme="dark"` CSS overrides
- [x] No white flash or unstyled content in dark mode

## Files Modified/Created

### Created
- `apps/tasks/migrations/0002_add_deadline_to_task.py` - Database migration
- `templates/projects/calendar.html` - Gantt chart template
- `test_issue24_calendar_acceptance.py` - Acceptance tests

### Modified
- `apps/tasks/models.py` - Added deadline field
- `apps/projects/views.py` - Added 3 calendar views
- `apps/projects/urls.py` - Added 3 calendar URLs
- `apps/tasks/views.py` - Updated create/edit to handle deadline
- `templates/partials/sidebar.html` - Added Calendar link
- `templates/tasks/create.html` - Added deadline field
- `templates/tasks/partials/slide_over.html` - Added deadline field

## Future Enhancements

Potential improvements for future iterations:

1. **Dependencies/Links**: Add task dependency arrows in Gantt
2. **Resource Histograms**: Show resource allocation over time
3. **Critical Path**: Highlight critical path through projects
4. **Baseline Tracking**: Compare actual vs. planned dates
5. **Export**: PDF/PNG export of Gantt chart
6. **Filters**: Filter by project, team, priority
7. **Zoom Levels**: Add day/week granularity
8. **Task Creation**: Create tasks directly from Gantt (right-click menu)
9. **Bulk Operations**: Select multiple projects to update dates
10. **Custom Fields**: Show priority, status in Gantt tooltips

## Performance Considerations

- **Query Optimization**: Uses `select_related()` for assigned users/teams to avoid N+1 queries
- **Filtering**: Pre-filters projects to user's accessible set before processing
- **Lazy Loading**: Gantt data fetched separately via AJAX (not embedded in HTML)
- **Resource Deduplication**: Uses set to track unique resources, prevents duplicates

## Browser Compatibility

DHTMLX Gantt supports:
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers (with touch support)

## License Compliance

DHTMLX Gantt GPL Version:
- ✅ Free for internal company use
- ✅ Free for open-source projects
- ❌ Requires commercial license for SaaS/redistribution
- Current usage: Internal project management (compliant)

## Summary

The Project Calendar & Resource Gantt feature is **fully implemented and tested**. All acceptance criteria pass. The implementation follows Friday's existing patterns for views, templates, and permissions. The feature seamlessly integrates with the existing project and task models without breaking changes.

**Status**: ✅ Ready for review and merge
