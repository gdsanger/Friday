# ISSUE-31: Task Dependencies Implementation Summary

## Overview
Successfully implemented task dependencies feature allowing tasks to have "blocked by" relationships. A task marked as blocked cannot be moved to "in progress" status until all blocking tasks are completed.

## Implementation Details

### 1. Model Layer (apps/tasks/models.py)

#### TaskDependency Model
- Created through model linking tasks via "blocked by" relationship
- Fields:
  - `task`: The task that is blocked
  - `blocked_by`: The task that must be completed first
  - `created_by`: User who created the dependency
  - `created_at`: Timestamp of dependency creation
- Constraints:
  - `unique_together` on (task, blocked_by) prevents duplicates
  - CASCADE deletion ensures cleanup when tasks are deleted

#### Task Model Enhancements
Added three helper properties:

```python
@property
def blocking_tasks(self):
    """Tasks that must be done before this task can start."""
    return Task.objects.filter(blocks_deps__task=self)

@property
def is_blocked(self):
    """True if any blocking task is not yet done."""
    return self.blocked_by_deps.exclude(
        blocked_by__status=Task.STATUS_DONE
    ).exists()

@property
def blocked_tasks(self):
    """Tasks that are waiting for this task to be done."""
    return Task.objects.filter(blocked_by_deps__blocked_by=self)
```

### 2. Views Layer (apps/tasks/views.py)

#### DependencyAddView
- HTMX endpoint: POST `/tasks/<pk>/dependencies/add/`
- Validates and creates dependencies
- Prevents:
  - Self-dependencies (400 error)
  - Simple circular dependencies (400 error)
- Returns updated dependency list partial

#### DependencyRemoveView
- HTMX endpoint: POST `/tasks/<pk>/dependencies/<dep_pk>/remove/`
- Removes specified dependency
- Returns updated dependency list partial

#### TaskStatusView Enhancement
- Added status guard to prevent blocked tasks from moving to "in_progress"
- Returns 409 (Conflict) status with blocked_warning.html template
- Shows list of blocking tasks that need completion

#### Context Updates
- Updated TaskDetailView and TaskDetailFullView to include `project_tasks` in context
- Required for dependency dropdown in templates

### 3. URL Configuration (apps/tasks/urls.py)

Added two new URL patterns:
```python
path('<int:pk>/dependencies/add/', views.DependencyAddView.as_view(), name='dependency-add'),
path('<int:pk>/dependencies/<int:dep_pk>/remove/', views.DependencyRemoveView.as_view(), name='dependency-remove'),
```

### 4. Templates

#### templates/tasks/partials/dependency_list.html
- Shows "Blockiert durch" (blocked by) section with:
  - Status badges
  - Clickable task titles (HTMX slide-over)
  - Remove buttons
- Shows "Blockiert diese Tasks" (blocking these tasks) section
- Add dependency form with dropdown and submit button
- Fully HTMX-powered with outerHTML swaps

#### templates/tasks/partials/blocked_warning.html
- Alert shown when trying to move blocked task to in_progress
- Lists all blocking tasks with their statuses
- Returns 409 status code

#### templates/tasks/partials/card.html
- Added blocked indicator badge:
  - Orange lock icon
  - "Blockiert" text
  - Appears below parent task indicator

#### templates/tasks/partials/slide_over.html
- Added Dependencies card section between task details and subtasks
- Includes dependency_list.html partial

#### templates/tasks/detail_full.html
- Added Dependencies card in right sidebar
- Positioned between task details and AI actions
- Includes dependency_list.html partial

### 5. Gantt Chart Integration (apps/projects/views.py)

Updated CalendarDataView to include dependency links:
```python
for dep in TaskDependency.objects.filter(
    task__project__in=projects
).select_related('task', 'blocked_by'):
    gantt_links.append({
        'id':     f'dep_{dep.pk}',
        'source': f't_{dep.blocked_by_id}',
        'target': f't_{dep.task_id}',
        'type':   '0',  # finish-to-start
    })
```

### 6. Database Migration

Created migration: `apps/tasks/migrations/0004_add_task_dependency.py`
- Creates `tasks_taskdependency` table
- Applied successfully

### 7. Testing

Created comprehensive test suite: `test_issue31_task_dependencies.py`

**All 17 tests passed:**
1. ✓ TaskDependency model creation
2. ✓ Unique together constraint
3. ✓ Task.blocking_tasks property
4. ✓ Task.is_blocked property (True)
5. ✓ Task.is_blocked property (False when blocker done)
6. ✓ Task.blocked_tasks property
7. ✓ Add dependency via DependencyAddView
8. ✓ Self-dependency rejection
9. ✓ Circular dependency rejection
10. ✓ Remove dependency via DependencyRemoveView
11. ✓ Blocked task status guard
12. ✓ Unblocked task status transition
13. ✓ Dependency section in slide-over
14. ✓ Dependency section in full detail
15. ✓ Blocking tasks shown in dependency list
16. ✓ Blocked tasks shown in dependency list
17. ✓ Gantt chart includes dependency links

## Acceptance Criteria Status

✅ **All acceptance criteria met:**

- [x] `TaskDependency` model exists and migrates cleanly
- [x] `Task.is_blocked` returns True when any blocking task is not done
- [x] `Task.blocking_tasks` returns correct queryset
- [x] Adding a dependency updates the dependency list via HTMX
- [x] Removing a dependency updates the dependency list via HTMX
- [x] Self-dependency is rejected (400)
- [x] Simple circular dependency is rejected (400)
- [x] Moving a blocked task to "In Progress" shows warning (409), does not move
- [x] Blocked tasks show a lock badge on Kanban cards
- [x] Dependency section appears in task slide-over and full detail
- [x] Gantt chart shows dependency arrows between milestone tasks

## Example Usage

1. **Add a dependency:**
   - Open task detail slide-over or full page
   - Go to Dependencies section
   - Select blocking task from dropdown
   - Click "Hinzufügen" (Add)

2. **Remove a dependency:**
   - Click the X button next to a blocking task

3. **Attempt to move blocked task:**
   - Try changing status to "In Progress"
   - System shows warning with list of blocking tasks
   - Task remains in current status

4. **View in Gantt:**
   - Tasks with deadlines show dependency arrows
   - Arrows indicate finish-to-start relationships

## Files Modified

1. `apps/tasks/models.py` - Added TaskDependency model and Task properties
2. `apps/tasks/views.py` - Added dependency views and status guard
3. `apps/tasks/urls.py` - Added dependency URL patterns
4. `apps/projects/views.py` - Added Gantt dependency links
5. `templates/tasks/partials/dependency_list.html` - New
6. `templates/tasks/partials/blocked_warning.html` - New
7. `templates/tasks/partials/card.html` - Added blocked indicator
8. `templates/tasks/partials/slide_over.html` - Added dependencies section
9. `templates/tasks/detail_full.html` - Added dependencies section
10. `apps/tasks/migrations/0004_add_task_dependency.py` - New migration

## Notes

- Dependencies use German UI text matching the rest of the application
- HTMX provides seamless user experience without page reloads
- Circular dependency detection is currently simple (direct circular only)
- More complex transitive circular dependencies could be detected with graph traversal if needed
- Gantt links only appear for tasks that have deadlines set

## Future Enhancements (Not in Current Scope)

- Transitive circular dependency detection
- Bulk dependency operations
- Dependency visualization/graph view
- Auto-suggest dependencies based on task relationships
- Email notifications when blocking tasks are completed
