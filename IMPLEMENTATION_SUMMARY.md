# ISSUE-02 Implementation Summary

## Overview
Successfully implemented all Django models and database architecture for the Friday project management system.

## Models Implemented

### apps/core/models.py
- **TimeStampedModel** - Abstract base model with `created_at` and `updated_at` fields
- **Organisation** - Singleton model (pk always 1) representing EOE organization

### apps/accounts/models.py
- **User** - Custom user model extending AbstractUser with:
  - Profile fields: avatar, display_name, job_title, phone
  - Azure SSO: azure_oid, azure_upn
  - Preferences: notify_email, notify_inapp, timezone
  - Properties: full_name, teams, initials

### apps/teams/models.py
- **Team** - Team model with name, slug, color, icon
- **TeamMembership** - Through model for User-Team relationships with roles (lead, member, guest)

### apps/projects/models.py
- **Project** - Project model with status, visibility, ownership
- **ProjectUserMembership** - Direct user membership with roles (manager, contributor, viewer)
- **ProjectTeamMembership** - Team membership with roles (contributor, viewer)
- Methods: `get_all_members()`, `is_member()`, `get_effective_role()`

### apps/tasks/models.py
- **Label** - Task labels with colors
- **Task** - Task model with:
  - Assignment: user OR team (both nullable)
  - Watchers: users AND/OR teams (ManyToMany)
  - Properties: assignee_display, is_overdue
  - Method: get_all_watchers()
- **Comment** - Task comments with optional AI summary
- **Attachment** - File attachments for tasks
- **TimeEntry** - Time tracking for tasks

### apps/ai/models.py
- **AIProviderConfig** - AI provider configuration with encrypted API keys
- **AIGlobalSettings** - Singleton (pk always 1) for global AI settings
- **AIUsageLog** - Log of AI API usage with token tracking

### apps/notifications/models.py
- **Notification** - In-app notifications using ContentTypes

## Database Features

### Indexes
- Task: (project, status), assigned_to_user, assigned_to_team, due_date
- Notification: (recipient, is_read)
- AIUsageLog: created_at, (user, created_at), (team, created_at)

### Encryption
- AIProviderConfig.api_key uses EncryptedCharField for secure storage

### Migrations
Created in correct order to avoid circular dependencies:
1. core
2. accounts
3. teams
4. projects
5. tasks
6. ai
7. notifications

### Initial Data
- Organisation singleton (pk=1, name='EOE')
- Two default teams: IUN and ISARtec

## Django Admin
All models registered with appropriate:
- list_display fields
- list_filter options
- search_fields
- readonly_fields for timestamps
- date_hierarchy where applicable

## Testing
Comprehensive acceptance criteria test script (`test_acceptance_criteria.py`) verifies:
- ✅ All 12 acceptance criteria pass
- ✅ Singleton models work correctly
- ✅ Model methods return expected values
- ✅ Database indexes exist
- ✅ Encryption works
- ✅ Admin registration complete

## Key Design Decisions

1. **Flexible Assignment**: Tasks can be assigned to users OR teams, allowing for team-based workflows
2. **Flexible Watching**: Tasks can be watched by individual users AND/OR teams
3. **Hybrid Membership**: Projects support both direct user membership and team-based membership
4. **Singleton Pattern**: Organisation and AIGlobalSettings use enforced singleton pattern
5. **Encrypted Secrets**: AI provider API keys stored encrypted at rest
6. **Generic Notifications**: Using ContentTypes for flexible notification targets

## Usage Examples

### Create Organisation
```python
from apps.core.models import Organisation
org = Organisation.get()  # Always returns pk=1
```

### Create User with Team
```python
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership

User = get_user_model()
user = User.objects.create_user(username='john', email='john@example.com')
team = Team.objects.get(slug='iun')
TeamMembership.objects.create(user=user, team=team, role='member')
```

### Create Project with Team
```python
from apps.projects.models import Project, ProjectTeamMembership

project = Project.objects.create(
    name='My Project',
    status=Project.STATUS_ACTIVE,
    owner=user
)
ProjectTeamMembership.objects.create(
    project=project,
    team=team,
    role='contributor'
)

# Get all members (includes team members)
members = project.get_all_members()
```

### Create Task
```python
from apps.tasks.models import Task

task = Task.objects.create(
    title='Implement feature',
    project=project,
    assigned_to_team=team,
    status=Task.STATUS_TODO,
    priority=Task.PRIORITY_HIGH
)

# Check assignment
print(task.assignee_display)  # "Team: IUN"
```

## Dependencies
All required packages already in requirements/base.txt:
- Django >= 5.1
- django-encrypted-model-fields >= 0.6
- Pillow >= 10.0 (for image fields)
