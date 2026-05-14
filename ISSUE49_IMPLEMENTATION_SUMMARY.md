# ISSUE-49 Implementation Summary

## Task Assignment XOR Constraint Fix

**Issue:** Tasks could be assigned to both a user AND a team simultaneously, causing:
- Duplicate notifications in daily digest
- Users receiving tasks they weren't directly responsible for
- Unclear task ownership

**Solution:** Enforce XOR constraint - tasks can be assigned to EITHER a user OR a team, never both.

---

## Implementation Details

### 1. Model Validation

**File:** `apps/tasks/models.py`

Added `clean()` and updated `save()` methods to enforce XOR constraint:

```python
def clean(self):
    """Validate that task is assigned to either user OR team, not both."""
    from django.core.exceptions import ValidationError
    if self.assigned_to_user_id and self.assigned_to_team_id:
        raise ValidationError(
            'Ein Task kann nicht gleichzeitig einem User '
            'und einem Team zugewiesen sein.'
        )

def save(self, *args, **kwargs):
    """Call clean() before saving to enforce XOR constraint."""
    self.clean()
    super().save(*args, **kwargs)
```

**Impact:** All future task saves will validate the XOR constraint at the model level.

---

### 2. Data Migration

**File:** `apps/tasks/migrations/0008_fix_assignment_xor.py`

Created migration to fix existing tasks with both assignments:

```python
def fix_double_assignments(apps, schema_editor):
    """
    Tasks die sowohl assigned_to_user als auch assigned_to_team haben:
    → assigned_to_team leeren (User hat Vorrang)
    """
    Task = apps.get_model('tasks', 'Task')
    double_assigned = Task.objects.filter(
        assigned_to_user__isnull=False,
        assigned_to_team__isnull=False,
    )
    count = double_assigned.count()
    if count > 0:
        double_assigned.update(assigned_to_team=None)
```

**Impact:** Cleans up historical data by keeping user assignment and clearing team assignment.

---

### 3. Daily Digest Query Fix

**File:** `apps/mail/tasks.py` (lines 164-192)

Updated queries to enforce XOR logic:

```python
# OLD (problematic)
overdue = Task.objects.filter(
    models.Q(assigned_to_user=user) |
    models.Q(assigned_to_team__in=my_teams),
    due_date__lt=today,
)

# NEW (XOR enforced)
overdue = Task.objects.filter(
    models.Q(assigned_to_user=user) |
    models.Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True),
    due_date__lt=today,
)
```

**Logic:**
- User gets tasks where `assigned_to_user = user` (direct assignment)
- User gets tasks where `assigned_to_team IN user_teams AND assigned_to_user IS NULL` (team assignment without user)
- User does NOT get tasks where `assigned_to_team IN user_teams AND assigned_to_user = someone_else`

**Impact:** Eliminates duplicate task notifications in daily digest emails.

---

### 4. Mail Dispatcher Update

**File:** `apps/mail/dispatcher.py` (lines 60-69)

Added explicit comments clarifying XOR logic:

```python
if recipient_type == 'assignee':
    # XOR: User direkt zugewiesen → nur dieser User
    # Nur Team zugewiesen → alle Teammitglieder
    if task.assigned_to_user and _wants_mail(task.assigned_to_user):
        emails.add(task.assigned_to_user.email)
    elif task.assigned_to_team:
        # Team zugewiesen, kein User → alle Teammitglieder
        for m in task.assigned_to_team.memberships.all():
            if _wants_mail(m.user):
                emails.add(m.user.email)
```

**Impact:** Ensures mail notifications respect XOR constraint (already had `elif`, now documented).

---

### 5. TaskAssignView XOR Enforcement

**File:** `apps/tasks/views.py` (lines 274-286)

Updated view to explicitly clear opposite field:

```python
# XOR enforcement: User gewählt → Team leeren, Team gewählt → User leeren
if user_id:
    task.assigned_to_user = User.objects.get(pk=user_id)
    task.assigned_to_team = None
elif team_id:
    task.assigned_to_team = Team.objects.get(pk=team_id)
    task.assigned_to_user = None
else:
    # Beide leer → Zuweisung aufheben
    task.assigned_to_user = None
    task.assigned_to_team = None
```

**Impact:** Backend enforces XOR when assignments are updated via HTMX.

---

### 6. UI JavaScript XOR Enforcement

**Files:**
- `templates/tasks/partials/slide_over.html` (lines 140-158)
- `templates/tasks/detail_full.html` (lines 225-243)
- `templates/tasks/create.html` (lines 179-190 - already existed)
- `templates/tasks/partials/create_slide_over.html` (lines 153-164 - already existed)

Added JavaScript to clear opposite dropdown on change:

```javascript
// XOR enforcement: Clear team when user selected, clear user when team selected
(function() {
    const userSelect = document.getElementById('assign-user-{{ task.pk }}');
    const teamSelect = document.getElementById('assign-team-{{ task.pk }}');
    if (userSelect && teamSelect) {
        userSelect.addEventListener('change', function() {
            if (this.value) {
                teamSelect.value = '';
            }
        });
        teamSelect.addEventListener('change', function() {
            if (this.value) {
                userSelect.value = '';
            }
        });
    }
})();
```

**Impact:** Immediate UI feedback - selecting user clears team, selecting team clears user.

---

## Test Coverage

**File:** `test_issue49_assignment_xor.py`

Comprehensive test suite with 5 test suites:

1. **Model Validation:** Tests Task.clean() rejects both assignments
2. **Data Migration:** Tests migration fixes double assignments
3. **Daily Digest Query:** Tests XOR logic prevents duplicate notifications
4. **Mail Dispatcher:** Tests assignee resolution respects XOR
5. **TaskAssignView:** Tests view enforces XOR when updating assignments

Run tests:
```bash
python test_issue49_assignment_xor.py
```

---

## Acceptance Criteria Status

### Model ✅
- [x] `Task.clean()` wirft ValidationError wenn beide Felder gesetzt
- [x] Data Migration bereinigt bestehende Tasks (User hat Vorrang)
- [x] `Task.save()` ruft `clean()` auf

### UI ✅
- [x] User-Dropdown wählen → Team wird automatisch geleert
- [x] Team-Dropdown wählen → User wird automatisch geleert
- [x] Task-Create-Form hat JavaScript XOR enforcement
- [x] Nie können beide Felder gleichzeitig einen Wert haben

### Digest ✅
- [x] Tasks mit `assigned_to_user=X` erscheinen nur bei User X
- [x] Tasks mit `assigned_to_team=T, assigned_to_user=NULL` erscheinen bei allen T-Mitgliedern
- [x] Tasks mit `assigned_to_user=X, assigned_to_team=T` erscheinen NUR bei X, nicht bei T
- [x] Kein User bekommt Tasks für die er nicht zuständig ist

### Mail Dispatcher ✅
- [x] `assigned_to_user` gesetzt → nur dieser User bekommt Mail
- [x] Nur `assigned_to_team` gesetzt → alle Teammitglieder bekommen Mail
- [x] Nie beide gleichzeitig (durch XOR fix bereits ausgeschlossen)

---

## Migration Instructions

To apply this fix to your installation:

```bash
# 1. Apply the data migration
python manage.py migrate tasks

# 2. Run tests to verify
python test_issue49_assignment_xor.py

# 3. Restart application
# (restart your Django/Celery processes)
```

---

## Technical Notes

### XOR Constraint Enforcement Layers

1. **Database Level:** Migration cleans existing data
2. **Model Level:** `clean()` validates on save
3. **View Level:** `TaskAssignView` explicitly clears opposite field
4. **UI Level:** JavaScript prevents selecting both simultaneously

This multi-layer approach ensures the constraint is enforced at all levels.

### Query Performance

The XOR query filter adds minimal overhead:
```python
Q(assigned_to_user=user) |
Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True)
```

Both conditions use indexed fields:
- `assigned_to_user` (indexed in Task model)
- `assigned_to_team` (indexed in Task model)

### Edge Cases Handled

1. **Unassigned tasks:** Both fields null is valid
2. **Historical data:** Migration fixes existing violations
3. **Direct DB manipulation:** Model validation catches on next save
4. **HTMX updates:** View enforces XOR on assignment changes
5. **Form submissions:** JavaScript prevents UI from sending both

---

## Related Issues

- **ISSUE-02** — Task model
- **ISSUE-34** — Mail Dispatcher
- **ISSUE-35** — Daily Digest

---

## Future Considerations

If you need to track "team context" while a user has the task, consider:
- Adding a separate `team_context` field (not mutually exclusive)
- Using task labels/tags to indicate team involvement
- Adding task watchers (teams can watch tasks they're interested in)

Do NOT remove the XOR constraint - it's critical for notification logic.
