# ISSUE-34: Mail Engine Implementation Summary

## Overview

This implementation provides a complete Mail Engine for the Friday project based on Microsoft Graph API with Client Credentials Flow. This is a **separate** mail system from the existing SSO-based mail service (ISSUE-03).

## Key Changes

### 1. Configuration (.env.example and settings)

**New Environment Variables:**
```bash
# Separate Azure App Registration for Mail
MAIL_AZURE_CLIENT_ID=your-mail-app-client-id
MAIL_AZURE_CLIENT_SECRET=your-mail-app-client-secret
MAIL_AZURE_TENANT_ID=your-azure-tenant-id

# System Mailbox
MAIL_FROM_ADDRESS=friday@isartec.de
MAIL_FROM_NAME=Friday
MAIL_SHARED_MAILBOX=friday@isartec.de

# Site URL for email links
SITE_URL=http://localhost:8011
```

**Settings Added** (config/settings/base.py):
- `MAIL_AZURE_CLIENT_ID`
- `MAIL_AZURE_CLIENT_SECRET`
- `MAIL_AZURE_TENANT_ID`
- `MAIL_FROM_ADDRESS`
- `MAIL_FROM_NAME`
- `MAIL_SHARED_MAILBOX`
- `SITE_URL`

### 2. New Mail Service (service_new.py)

**File:** `apps/mail/service_new.py`

Complete rewrite using Client Credentials Flow:
- `MailService._get_token()` - Gets app token via Client Credentials (cached 55 min)
- `MailService.send()` - Sends mail from system mailbox
- `MailService.send_template()` - Renders template and sends
- `MailServiceError` - Custom exception class

**Key Difference from Old Service:**
- No user token required
- Uses application permissions, not delegated permissions
- Sends from shared mailbox, not from user
- Token cached in Redis

### 3. Template Renderer (templates.py)

**File:** `apps/mail/templates.py`

- `render_mail_template()` - Renders HTML templates with base context
- Automatically adds: app_name, app_url, from_name, from_address, support_url

### 4. HTML Mail Templates

**Directory:** `templates/mail/`

**Created Templates:**
1. `base.html` - Outlook-compatible base template with Friday branding
2. `task_assigned.html` - Task assignment notification
3. `task_done.html` - Task completion notification
4. `task_comment.html` - New comment notification
5. `task_overdue.html` - Overdue task alert
6. `task_created.html` - New task notification
7. `portal_ticket_created.html` - Portal ticket confirmation
8. `portal_ticket_done.html` - Portal ticket completion
9. `daily_digest.html` - Daily task summary
10. `user_invited.html` - User invitation email

**Template Features:**
- Outlook-compatible table-based layout
- Responsive design
- Info boxes for structured data
- Status badges (green, blue, yellow, red)
- CTA buttons linking to tasks
- Consistent Friday branding

### 5. MailHook Model

**File:** `apps/mail/models.py`

New model for configurable mail triggers:

**Fields:**
- `event` - Hook event type (unique)
- `is_active` - Toggle hook on/off
- `recipients` - JSON list of recipient types
- `template_name` - Template filename
- `subject_template` - Subject with placeholders
- `description` - Human-readable description

**Event Types:**
- `task_created`
- `task_assigned`
- `task_done`
- `task_comment`
- `task_overdue`
- `portal_ticket_created`
- `portal_ticket_done`
- `daily_digest`
- `user_invited`

**Recipient Types:**
- `assignee` - Assigned user/team members
- `creator` - Task creator
- `watchers` - Users/teams watching the task
- `project_manager` - Project managers
- `portal_user` - Portal user (task creator)

**Admin Integration:** Registered in admin.py with fieldsets

### 6. Management Command

**File:** `apps/mail/management/commands/seed_mail_hooks.py`

**Usage:** `python manage.py seed_mail_hooks`

**Features:**
- Idempotent (safe to run multiple times)
- Creates 8 default mail hooks
- Updates template/subject on re-run
- Preserves is_active state
- Color-coded output

**Default Hooks:**
- task_assigned - Active
- task_done - Active
- task_comment - **Inactive** (default off)
- task_overdue - Active
- portal_ticket_created - Active
- portal_ticket_done - Active
- daily_digest - Active
- user_invited - Active

### 7. Mail Dispatcher

**File:** `apps/mail/dispatcher.py`

Central mail dispatch system:

**Functions:**
- `dispatch()` - Main entry point for all mail notifications
- `_resolve_recipients()` - Converts recipient types to email addresses
- `_wants_mail()` - Checks user.notify_email preference

**Features:**
- Checks if hook is active
- Resolves recipients based on task relationships
- Respects user mail preferences
- Renders subject with context
- Dispatches Celery tasks

### 8. Celery Tasks

**File:** `apps/mail/tasks.py`

**New Tasks:**

1. **send_hook_mail** (Celery shared_task)
   - Sends individual mail via MailService
   - Retries 3 times on failure (60s delay)
   - Logs success/failure

2. **send_daily_digest** (Celery Beat - 07:00)
   - Sends daily summary to all active users
   - Includes overdue tasks
   - Includes open tasks (max 10)
   - Skips users with no tasks

3. **send_overdue_notifications** (Celery Beat - 08:00)
   - Notifies assignees about overdue tasks
   - One notification per overdue task
   - Only for tasks with assigned_to_user

**Existing Tasks (Preserved):**
- `process_incoming_mail` - Handles incoming webhook mail
- `renew_webhook_subscriptions` - Renews Graph API subscriptions

### 9. Celery Beat Schedule

**File:** `config/celery.py`

**Updated Schedule:**
```python
{
    'renew-webhook-subscriptions': {
        'task': 'apps.mail.tasks.renew_webhook_subscriptions',
        'schedule': crontab(hour=6, minute=0),
    },
    'daily-digest': {
        'task': 'apps.mail.tasks.send_daily_digest',
        'schedule': crontab(hour=7, minute=0),
    },
    'overdue-notifications': {
        'task': 'apps.mail.tasks.send_overdue_notifications',
        'schedule': crontab(hour=8, minute=0),
    },
}
```

### 10. Database Migration

**File:** `apps/mail/migrations/0002_add_mail_hook.py`

Creates the MailHook model table with all fields.

## Azure App Registration Requirements

**IMPORTANT:** A separate Azure App Registration is required for the Mail Engine.

**Configuration:**
```
Name:        Friday Mail Service
Type:        Web Application
Auth Flow:   Client Credentials (no user, no redirect URI)
```

**Required Permissions (Application, not Delegated):**
- `Mail.Send` - Send mail as any user
- `Mail.ReadWrite` - Read/write mail (for webhooks)
- `User.Read.All` - Look up recipient users

**Admin Consent:** Required

## Next Steps for Full Integration

### 1. Add Dispatcher Calls to Views

The dispatcher needs to be called from task views when events occur:

**Example locations:**
- `apps/tasks/views.py` - Task assignment, status changes
- `apps/tasks/views.py` - Comment creation
- Portal views - Ticket creation/completion
- User invite views

**Example Usage:**
```python
from apps.mail.dispatcher import dispatch
from django.conf import settings

# After task assignment:
dispatch(
    event='task_assigned',
    context={
        'recipient_name': task.assigned_to_user.full_name,
        'assigned_by': request.user.full_name,
        'task_title': task.title,
        'task_url': f'{settings.SITE_URL}/tasks/{task.pk}/',
        'project_name': task.project.name,
        'due_date': task.due_date.strftime('%d.%m.%Y') if task.due_date else '',
        'priority': task.get_priority_display(),
    },
    task=task,
)
```

### 2. Run Migrations

```bash
python manage.py migrate mail
```

### 3. Seed Mail Hooks

```bash
python manage.py seed_mail_hooks
```

### 4. Configure Environment

1. Create separate Azure App Registration
2. Add credentials to `.env`
3. Configure shared mailbox
4. Set SITE_URL

### 5. Test Mail Sending

**Manual Test:**
```python
from apps.mail.service_new import MailService

MailService.send_template(
    to=['test@example.com'],
    template_name='task_assigned',
    subject='Test Mail',
    context={
        'recipient_name': 'Test User',
        'assigned_by': 'Admin',
        'task_title': 'Test Task',
        'task_url': 'http://localhost:8011/tasks/1/',
        'project_name': 'Test Project',
    }
)
```

### 6. Admin Panel UI (Optional - Phase 2)

Create admin panel views for:
- `/admin-panel/mail/hooks/` - List all hooks
- `/admin-panel/mail/hooks/<event>/` - Edit hook (toggle + recipients)
- `/admin-panel/mail/settings/` - Mailbox configuration
- `/admin-panel/mail/log/` - Sent mail log

## File Structure

```
apps/mail/
├── __init__.py
├── admin.py                          # Admin registration (updated)
├── models.py                         # Added MailHook model
├── service.py                        # OLD service (ISSUE-03, preserved)
├── service_new.py                    # NEW service (ISSUE-34)
├── templates.py                      # Template renderer (NEW)
├── dispatcher.py                     # Mail dispatcher (NEW)
├── tasks.py                          # Celery tasks (updated)
├── views.py                          # Webhook views (existing)
├── urls.py                           # URL config (existing)
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── seed_mail_hooks.py       # Seeding command (NEW)
└── migrations/
    ├── 0001_initial.py              # Existing
    └── 0002_add_mail_hook.py        # NEW

templates/mail/
├── base.html                         # Base template (NEW)
├── task_assigned.html               # NEW
├── task_done.html                   # NEW
├── task_comment.html                # NEW
├── task_overdue.html                # NEW
├── task_created.html                # NEW
├── portal_ticket_created.html       # NEW
├── portal_ticket_done.html          # NEW
├── daily_digest.html                # NEW
└── user_invited.html                # NEW
```

## Testing Strategy

### Unit Tests
- MailService token caching
- Template rendering with context
- Dispatcher recipient resolution
- Hook activation/deactivation

### Integration Tests
- End-to-end mail sending
- Celery task execution
- Beat schedule timing
- User preference handling

### Manual Tests
1. Send test mail via Django shell
2. Trigger task assignment
3. Test daily digest (time travel)
4. Test overdue notifications
5. Verify Outlook rendering

## Backwards Compatibility

**OLD Service (ISSUE-03):**
- `service.py` - Preserved unchanged
- Uses SSO tokens (delegated permissions)
- User-based mail sending

**NEW Service (ISSUE-34):**
- `service_new.py` - System-wide mail service
- Uses Client Credentials (application permissions)
- System mailbox sending

**Coexistence:**
- Both services can run simultaneously
- Old service for user-initiated actions
- New service for system notifications

## Known Limitations

1. **No Admin Panel UI** - Only Django admin interface
2. **No Mail Log** - Mail sending not tracked in DB
3. **No Retry Visibility** - Celery retries not exposed to users
4. **No Unsubscribe Link** - Users toggle via profile settings
5. **No Template Previews** - Templates must be tested manually
6. **No A/B Testing** - Single template per event
7. **No Localization** - All templates in English
8. **No HTML/Plain Text** - Only HTML mails sent

## Security Considerations

1. **Token Storage** - App token cached in Redis (55 min)
2. **Credentials** - Client secret in .env (encrypted at rest)
3. **Permissions** - Application permissions require admin consent
4. **Mailbox Access** - Shared mailbox accessible by app
5. **User Privacy** - notify_email preference respected
6. **Rate Limiting** - No rate limiting implemented
7. **Input Validation** - Template context not sanitized

## Performance

- **Token Caching** - 55 minutes (5 min buffer)
- **Celery Tasks** - Asynchronous, non-blocking
- **Retry Strategy** - 3 retries with 60s delay
- **Batch Processing** - Daily digest batched by user
- **Database Queries** - N+1 queries in recipient resolution

## Monitoring & Debugging

**Logs:**
- `logger.info()` - Successful mail sends
- `logger.error()` - Failed mail sends
- `logger.warning()` - Missing tasks/users

**Celery Logs:**
- Worker logs show task execution
- Beat logs show schedule execution
- Retry logs show failure recovery

**Django Admin:**
- MailHook list shows active/inactive hooks
- UserMailToken shows token expiry (for old service)

## Support & Troubleshooting

**Common Issues:**

1. **Mail not sending**
   - Check hook is active in admin
   - Check user.notify_email = True
   - Check MAIL_AZURE_* credentials
   - Check Celery worker running

2. **Token errors**
   - Verify app registration permissions
   - Check admin consent granted
   - Verify tenant ID correct
   - Check client secret not expired

3. **Template errors**
   - Check template file exists
   - Check context variables provided
   - Check template syntax valid

4. **Recipient errors**
   - Check task relationships (assignee, watchers)
   - Check user email not empty
   - Check notify_email preference

5. **Celery errors**
   - Check Redis connection
   - Check Celery worker running
   - Check Beat schedule active

## Documentation References

- **ISSUE-34** - Original feature specification
- **ISSUE-03** - Old mail service (SSO-based)
- **ISSUE-05** - SSO implementation
- Microsoft Graph API - Mail.Send documentation
- MSAL Python - Client Credentials Flow

---

**Implementation Date:** 2026-05-13
**Author:** Claude (AI Agent)
**Status:** Core implementation complete, view integration pending
