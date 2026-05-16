# ISSUE-62: Labels/Tags für Tasks - Implementation Summary

## Overview
This implementation adds a complete Labels/Tags system to Friday, allowing tasks to be categorized and filtered across projects using labels.

## Components Implemented

### 1. Backend Views (apps/tasks/views.py)

#### Label Management Views
- **LabelListView**: Displays all labels with task counts (accessible to all users)
- **LabelCreateView**: Staff-only view to create new labels
- **LabelEditView**: Staff-only view to edit label name and color
- **LabelDeleteView**: Staff-only deletion (prevented if label has tasks)
- **LabelTasksView**: Project-wide Kanban view filtered by specific label

#### Task Label Assignment Views (HTMX)
- **TaskLabelAddView**: Adds label to task, returns updated label_list partial
- **TaskLabelRemoveView**: Removes label from task, returns updated label_list partial

### 2. URL Patterns (apps/tasks/urls.py)

```python
path('labels/',                              views.LabelListView.as_view(),           name='label-list'),
path('labels/create/',                       views.LabelCreateView.as_view(),         name='label-create'),
path('labels/<int:pk>/edit/',                views.LabelEditView.as_view(),           name='label-edit'),
path('labels/<int:pk>/delete/',              views.LabelDeleteView.as_view(),         name='label-delete'),
path('labels/<int:pk>/tasks/',               views.LabelTasksView.as_view(),          name='label-tasks'),
path('<int:pk>/labels/add/',                 views.TaskLabelAddView.as_view(),        name='task-label-add'),
path('<int:pk>/labels/<int:label_pk>/remove/', views.TaskLabelRemoveView.as_view(),   name='task-label-remove'),
```

### 3. Templates

#### Label Management
- **templates/tasks/labels/list.html**: Label list with create/edit/delete actions
- **templates/tasks/labels/form.html**: Label create/edit form with color picker
- **templates/tasks/labels/tasks.html**: Kanban board filtered by label

#### Task Integration
- **templates/tasks/partials/label_list.html**: Reusable label assignment widget
  - Shows current labels with remove buttons
  - Dropdown to add new labels (excludes already-assigned)
  - Uses HTMX for dynamic updates

#### UI Updates
- **templates/tasks/partials/card.html**: Added label badges display
- **templates/tasks/partials/slide_over.html**: Added labels section
- **templates/tasks/detail_full.html**: Added labels section
- **templates/partials/sidebar.html**: Added Labels navigation link
- **templates/kanban/board.html**: Added label filter dropdown

### 4. Kanban Integration (apps/kanban/views.py)

- Added label filter: `tasks.filter(labels__pk=label_id)`
- Labels context with task count annotation
- Filter preserved across other filter changes

## Key Features

### Permission Model
- **All Users**: Can view labels, view label tasks, assign/remove labels on accessible tasks
- **Staff Only**: Can create, edit, and delete labels

### Label Management
- Unique label names enforced
- Custom colors via color picker
- Task count displayed on label list
- Labels with tasks cannot be deleted (protection with error message)

### Task Assignment
- HTMX-based dynamic assignment (no page reload)
- Dropdown shows only unassigned labels
- Remove button on each assigned label badge
- Clicking label badge navigates to label tasks view

### Display
- Labels shown as colored badges on Kanban cards
- Labels section in task detail views
- Label filter in Kanban board
- Project-wide label tasks view with Kanban layout

### Context Management
- `available_labels` context: Excludes already-assigned labels from dropdown
- Task count annotation on labels
- Filter state preservation across all Kanban filters

## Technical Patterns

### HTMX Pattern
Similar to watchers feature:
1. POST request to add/remove endpoint
2. Returns updated partial HTML
3. Uses `hx-target="#task-labels"` and `hx-swap="outerHTML"`
4. Auto-submit on dropdown selection change

### Staff Permission Check
```python
def dispatch(self, request, *args, **kwargs):
    if not request.user.is_staff:
        raise PermissionDenied
    return super().dispatch(request, *args, **kwargs)
```

### Filter Integration
All Kanban filter dropdowns include `[name='label']` in `hx-include` attribute to preserve label filter when other filters change.

## Database
No migrations needed - Label model and Task.labels ManyToMany relationship already existed from ISSUE-02.

## Acceptance Criteria Status

✅ `/tasks/labels/` lists all labels with task count
✅ Label name is clickable → filtered task view
✅ Only Staff can create and edit labels
✅ Label with tasks cannot be deleted (shows error)
✅ Label without tasks can be deleted
✅ Duplicate label names prevented
✅ Label dropdown in task slide-over and full-detail
✅ Dropdown shows only unassigned labels
✅ Selection adds label via HTMX immediately
✅ `×` button removes label via HTMX
✅ Clicking label badge opens filtered task view
✅ `/tasks/labels/<pk>/tasks/` shows all tasks with label
✅ Project-wide view, only accessible projects
✅ Kanban layout with status columns
✅ Project name visible on each card
✅ Back link to label list
✅ Label dropdown in Kanban filter bar
✅ Only labels with at least one task in dropdown
✅ Filter combinable with other filters

## Testing Notes

- Python syntax validation: ✅ Passed
- Template structure validation: ✅ Passed
- Manual testing requires environment setup (Django + database)

## Files Modified

1. `apps/tasks/views.py` - Added 7 new views + context updates
2. `apps/tasks/urls.py` - Added 7 new URL patterns
3. `apps/kanban/views.py` - Added label filter and context
4. `templates/tasks/labels/` - 3 new templates (list, form, tasks)
5. `templates/tasks/partials/label_list.html` - New partial
6. `templates/tasks/partials/card.html` - Added label display
7. `templates/tasks/partials/slide_over.html` - Added labels section
8. `templates/tasks/detail_full.html` - Added labels section
9. `templates/partials/sidebar.html` - Added Labels link
10. `templates/kanban/board.html` - Added label filter

## Usage Examples

### Creating a Label (Staff)
1. Navigate to Labels from sidebar
2. Click "+ Neues Label"
3. Enter name (e.g., "Q3-Release")
4. Pick color
5. Save

### Assigning Labels to Task
1. Open task detail (slide-over or full page)
2. Scroll to Labels section
3. Select label from dropdown
4. Label appears immediately

### Filtering by Label
1. Go to Kanban board
2. Select label from "Label" filter dropdown
3. Board shows only tasks with that label

### Viewing All Tasks for a Label
1. Go to Labels page
2. Click on label name
3. See Kanban view of all tasks with that label across projects
