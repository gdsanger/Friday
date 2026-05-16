# ISSUE-61 Implementation Summary

## Feature: Task in anderes Projekt verschieben

This feature allows project managers and staff to move tasks (along with their subtasks) to another accessible project.

## Implementation Details

### 1. URL Routes (`apps/tasks/urls.py`)

Added two new URL patterns:
- `task-move-project-form` → GET `/tasks/<pk>/move-project/form/` → Returns modal form
- `task-move-project` → POST `/tasks/<pk>/move-project/` → Executes the move

### 2. Views (`apps/tasks/views.py`)

#### TaskMoveProjectFormView (lines 873-900)
- **Purpose**: Returns modal form for selecting target project
- **Permissions**: Manager of source project OR staff member
- **Logic**:
  - Checks user has manager role in source project or is staff
  - Queries accessible projects (user is member OR user's teams are members)
  - Excludes current project from dropdown
  - Excludes archived projects from dropdown
  - Orders projects by name
- **Returns**: `move_project_form.html` template

#### TaskMoveProjectView (lines 903-952)
- **Purpose**: Executes the task move operation
- **Permissions**:
  - Manager of source project OR staff (to move from)
  - Member of target project (to move to)
- **Logic**:
  1. Validates `project_id` parameter exists
  2. Checks source project permissions (manager or staff)
  3. Checks target project membership
  4. Moves task to new project
  5. Inherits client from new project if task has no direct client
  6. Moves all subtasks to new project
  7. Resolves dependencies:
     - Deletes dependencies where task is blocked by tasks in old project
     - Deletes dependencies where task blocks tasks in old project
- **Returns**: 204 No Content with `HX-Trigger: taskMoved` header

### 3. Template (`templates/tasks/partials/move_project_form.html`)

Modal form structure:
- **Header**: Title with icon and close button
- **Body**:
  - Shows current project (color-coded, read-only)
  - Dropdown to select target project (required field)
  - Shows client name for each project (if exists)
  - Info message if subtasks exist (shows count)
- **Footer**: Cancel and Submit buttons

### 4. UI Integration

#### Slide-Over Template (`templates/tasks/partials/slide_over.html`)
- Added button in actions dropdown (lines 37-49)
- Button only visible to managers and staff
- Uses HTMX to load modal form
- Added modal container at end of file (lines 422-430)

#### Full Detail Template (`templates/tasks/detail_full.html`)
- Added button in actions dropdown (lines 52-64)
- Button only visible to managers and staff
- Uses HTMX to load modal form
- Added modal container at end of file (lines 371-379)

### 5. JavaScript Event Handler (`static/js/friday.js`)

Added `taskMoved` event handler (lines 522-539):
- Closes the move modal
- Refreshes Kanban board (if visible)
- Closes slide-over (task is now in another project)

## Permission Model

### To Move Task (Source Project):
- User must be **manager** of source project, OR
- User must be **staff**

### To Move To Project (Target Project):
- User must be **member** of target project (any role)

## Business Logic

### Task Move:
- Updates `task.project` to new project
- Updates `task.client` to new project's client (only if task has no direct client)

### Subtasks:
- All subtasks are automatically moved to new project
- Uses `task.subtasks.all().update(project=new_project)`

### Dependencies:
Dependencies to/from tasks in the old project are resolved:
1. **Blocking dependencies**: If task is blocked by tasks in old project → deleted
2. **Blocked dependencies**: If task blocks tasks in old project → deleted

This prevents broken dependencies across project boundaries.

### Client Inheritance:
- If `task.client` is NULL → inherits `new_project.client`
- If `task.client` is set → keeps existing client

## User Experience Flow

1. User opens task detail (slide-over or full page)
2. User clicks actions menu (⋮)
3. User clicks "In anderes Projekt verschieben" (only visible to managers/staff)
4. Modal opens showing:
   - Current project
   - Dropdown of accessible target projects
   - Info about subtasks (if any)
5. User selects target project
6. User clicks "Verschieben"
7. Server validates permissions and executes move
8. Modal closes, Kanban refreshes, Slide-over closes
9. Task is now in new project with all subtasks

## Acceptance Criteria Coverage

✅ "In anderes Projekt verschieben" Button im Task Actions Menü
✅ Nur Projektmanager und Staff können verschieben
✅ Modal zeigt aktuelles Projekt + Dropdown mit zugänglichen Zielprojekten
✅ Aktuelles Projekt erscheint nicht im Dropdown
✅ Archivierte Projekte erscheinen nicht im Dropdown
✅ Verschieben aktualisiert `task.project`
✅ Subtasks werden automatisch mitgeschoben
✅ Client wird aus neuem Projekt übernommen (wenn task.client leer)
✅ Abhängigkeiten zu Tasks im alten Projekt werden aufgelöst
✅ Info-Hinweis wenn Subtasks vorhanden
✅ Nach Verschieben: Modal schließt, Kanban aktualisiert, Slide-Over schließt

## Testing

A comprehensive test suite has been created in `test_issue61_move_task_project.py` covering:
- Permission requirements (manager/staff)
- Project list filtering (accessible, non-archived, excluding current)
- Task and subtask movement
- Client inheritance
- Dependency resolution
- Error cases (missing project_id, no access to target)

## Dependencies on Other Issues

- **ISSUE-02**: Task, Project models ✅
- **ISSUE-08**: Task Actions Menu ✅
- **ISSUE-31**: TaskDependency (resolved during move) ✅

## Files Modified

1. `apps/tasks/urls.py` - Added URL patterns
2. `apps/tasks/views.py` - Added TaskMoveProjectFormView and TaskMoveProjectView
3. `templates/tasks/partials/move_project_form.html` - New modal template
4. `templates/tasks/partials/slide_over.html` - Added button and modal container
5. `templates/tasks/detail_full.html` - Added button and modal container
6. `static/js/friday.js` - Added taskMoved event handler

## Files Created

1. `templates/tasks/partials/move_project_form.html` - Modal form template
2. `test_issue61_move_task_project.py` - Acceptance test suite
