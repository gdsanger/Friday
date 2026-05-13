# ISSUE-28: Customer Portal - Implementation Summary

## Overview
Successfully implemented the Customer Portal feature allowing external users (university staff) to submit and track tickets through a restricted interface.

## Implementation Components

### 1. User Model Extension ✓
- Added `portal_client` ForeignKey field to User model
- Migration created: `0003_add_portal_client.py`
- Links portal users to specific clients for scoped access

### 2. Portal App Structure ✓
```
apps/portal/
├── __init__.py
├── apps.py
├── middleware.py        # PortalUserMiddleware - restricts access
├── mixins.py           # PortalUserRequiredMixin
├── urls.py             # Portal URL routing
└── views.py            # All portal views
```

### 3. Middleware ✓
- `PortalUserMiddleware` restricts portal users to portal-only paths
- Blocks access to `/dashboard/`, `/kanban/`, `/tasks/`, etc.
- Allows access to `/portal/`, `/accounts/`, `/static/`, `/media/`

### 4. Views Implemented ✓
- `PortalHomeView` - Dashboard with KPIs and recent tickets
- `PortalTemplateSelectView` - Template selection (global + client-specific)
- `PortalTicketCreateView` - Create tickets from templates
- `PortalTicketListView` - List own tickets with filters
- `PortalTicketDetailView` - View ticket details
- `PortalTicketCommentView` - Add comments (HTMX)
- `PortalTicketAttachmentView` - Upload attachments (HTMX)

### 5. Templates ✓
```
templates/portal/
├── base_portal.html          # Minimal layout without sidebar
├── home.html                 # Portal dashboard
├── template_select.html      # Template selection with cards
├── ticket_create.html        # Ticket creation form
├── ticket_list.html          # Ticket list with filters
├── ticket_detail.html        # Ticket detail view
└── partials/
    ├── comment_list.html     # Comment list (HTMX target)
    └── attachment_list.html  # Attachment list (HTMX target)
```

### 6. CSS Styling ✓
Added to `static/css/friday.css`:
- `.portal-template-card` - Template selection cards
- `.portal-template-icon`, `.portal-template-name`, etc.
- `.portal-layout` - Portal-specific layout
- `.avatar-circle` - Comment avatars
- Hover effects and transitions

### 7. Login Redirect Logic ✓
Updated `apps/accounts/views.py`:
- `AzureCallbackView` checks `user.is_portal_user` and redirects to portal
- `StandardLoginView` checks `user.is_portal_user` and redirects to portal
- Regular users continue to be redirected to `/dashboard/`

### 8. Admin Panel Integration ✓
- Updated `AdminUserDetailView` to include clients in context
- Added `AdminUserPortalSettingsView` for managing portal settings
- Updated user detail template with portal settings form
- Added portal badge to user row template
- URL route: `/admin-panel/users/<pk>/portal/`

## Acceptance Criteria Verification

### Auth & Routing ✓
- [x] Portal users redirected to `/portal/` after login
- [x] `PortalUserMiddleware` prevents access to `/dashboard/`, `/kanban/`, etc.
- [x] Non-portal users get 403 on `/portal/*` (PortalUserRequiredMixin)
- [x] Logout works from portal (standard Django logout)

### Template Selection ✓
- [x] Global templates (client=None) displayed to all portal users
- [x] Client-specific templates displayed to matching users
- [x] `is_portal_visible=False` templates are hidden
- [x] Foreign client templates are hidden (permission check)
- [x] Cards show name, description, field count
- [x] Hover effects on cards (CSS transitions)
- [x] Empty state when no templates available
- [x] Two groups: client-specific and global

### Ticket Creation ✓
- [x] Form includes: title, description (EasyMDE), due_date, priority, attachments
- [x] Due date field labeled "Wunschtermin"
- [x] YAML extra fields rendered dynamically
- [x] Validation for required fields
- [x] Multiple file uploads supported
- [x] `task.requester = request.user`
- [x] `task.project = template.default_project`
- [x] `task.assigned_to_team = template.default_assigned_to_team`
- [x] Mail hook triggered: `EVENT_PORTAL_CREATED`
- [x] Redirect to ticket detail after creation

### Ticket Overview ✓
- [x] Only tickets with `requester=request.user` shown
- [x] Status filter tabs functional
- [x] Pagination for > 20 tickets (paginate_by=20)

### Ticket Detail ✓
- [x] Only own tickets accessible (requester=user), 404 otherwise
- [x] Description rendered as Markdown
- [x] Status badges in German (portal_status dictionary)
- [x] Comment form via HTMX
- [x] Attachment download + upload via HTMX

### Admin Panel ✓
- [x] `is_portal_user` toggle in user detail page
- [x] `portal_client` dropdown in user detail page
- [x] Portal badge shown in user list
- [x] Portal users don't see internal Friday data (via middleware)

## Technical Implementation Notes

### Template Visibility Logic
```python
TaskTemplate.objects.filter(
    is_active=True,
    is_portal_visible=True,
).filter(
    models.Q(client__isnull=True) |  # Global templates
    models.Q(client=client)           # Client-specific templates
)
```

### Permission Enforcement
```python
class PortalUserRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_portal_user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

### Middleware Protection
```python
PORTAL_PATHS = ('/portal/', '/accounts/', '/static/', '/media/')

if (request.user.is_authenticated
        and request.user.is_portal_user
        and not any(request.path.startswith(p) for p in PORTAL_PATHS)):
    return redirect('portal-home')
```

## Database Changes

### Migration: `0003_add_portal_client`
```python
operations = [
    migrations.AddField(
        model_name='user',
        name='portal_client',
        field=models.ForeignKey(
            blank=True,
            help_text='Client/Mandant assignment for portal users',
            null=True,
            on_delete=django.db.models.deletion.SET_NULL,
            related_name='portal_users',
            to='core.client'
        ),
    ),
]
```

## Integration Points

### Mail Engine Integration
- Event: `MailHook.EVENT_PORTAL_CREATED`
- Context includes: recipient_name, task_title, task_url, template_name, client_name
- Triggered on ticket creation

### Task Model Integration
- Uses existing `Task.requester` field (added in ISSUE-38)
- Uses existing `Task.template` FK (added in ISSUE-40)
- Uses existing `Task.client` FK (added in ISSUE-27)
- Integrates with `Comment` and `Attachment` models

### Template System Integration
- Leverages `TaskTemplate.get_extra_fields()` for YAML parsing
- Uses `template_utils.validate_extra_fields()` for validation
- Uses `template_utils.render_extra_fields_to_description()` for markdown generation
- Reuses `templates/tasks/templates/partials/_field.html` for field rendering

## URL Structure
```
/portal/                               → Portal home
/portal/tickets/                       → Ticket list
/portal/tickets/new/                   → Template selection
/portal/tickets/new/<slug>/            → Ticket creation
/portal/tickets/<pk>/                  → Ticket detail
/portal/tickets/<pk>/comment/          → Add comment (HTMX)
/portal/tickets/<pk>/attachment/       → Add attachment (HTMX)
```

## Frontend Features

### HTMX Integration
- Comments: `hx-post`, `hx-target="#comment-list"`, `hx-swap="outerHTML"`
- Attachments: `hx-post`, `hx-target="#attachment-list"`, `hx-swap="outerHTML"`
- Form submissions update content without page reload

### Markdown Support
- EasyMDE editor for ticket descriptions
- `marked.js` + `DOMPurify` for rendering
- Consistent with main Friday UI

### Theme Support
- Dark/light theme toggle in portal topbar
- Uses Friday CSS variables for consistent styling
- Theme preference stored in localStorage

## Testing
Comprehensive test suite created in `test_issue28_customer_portal.py`:
- Portal authentication and routing tests
- Template visibility and selection tests
- Ticket creation and validation tests
- Ticket list and detail view tests
- Admin panel portal management tests

## Dependencies Met
- ✓ ISSUE-02: Task, User, Attachment, Comment models
- ✓ ISSUE-27: Client model
- ✓ ISSUE-34: Mail Engine (portal notification events)
- ✓ ISSUE-38: Task.requester field
- ✓ ISSUE-40: TaskTemplate + YAML fields
- ✓ ISSUE-41: EasyMDE Markdown Editor

## Configuration Required

### Settings Updated
```python
INSTALLED_APPS = [
    ...
    'apps.portal',
]

MIDDLEWARE = [
    ...
    'django_htmx.middleware.HtmxMiddleware',
    'apps.portal.middleware.PortalUserMiddleware',  # After HtmxMiddleware
    ...
]
```

### URL Configuration
```python
# config/urls.py
urlpatterns = [
    ...
    path('portal/', include('apps.portal.urls')),
    ...
]
```

## Security Considerations

1. **Access Control**: PortalUserRequiredMixin ensures only portal users access portal
2. **Data Isolation**: QuerySets filter by `requester=request.user`
3. **Template Scoping**: Client-specific templates only visible to matching users
4. **Middleware Protection**: Prevents portal users from accessing internal tools
5. **CSRF Protection**: All forms include CSRF tokens
6. **Permission Checks**: Foreign client templates return 403

## Performance Optimizations

1. **Prefetching**: `.prefetch_related('comments__author', 'attachments__uploaded_by')`
2. **Select Related**: `.select_related('project')` for list views
3. **Pagination**: 20 tickets per page to prevent large result sets
4. **Indexing**: Leverages existing database indexes on User and Task models

## Future Enhancements (Not in Scope)

- Email notifications for ticket status changes (requires ISSUE-34 completion)
- Portal user dashboard widgets
- Ticket search functionality
- Export ticket history
- Bulk ticket operations
- Portal analytics for staff

## Files Modified/Created

### Modified Files
- `apps/accounts/models.py` - Added portal_client field
- `apps/accounts/views.py` - Added portal redirect logic
- `apps/admin_panel/views.py` - Added portal settings view
- `apps/admin_panel/urls.py` - Added portal settings URL
- `config/settings/base.py` - Added portal app and middleware
- `config/urls.py` - Added portal URL include
- `static/css/friday.css` - Added portal CSS
- `templates/admin_panel/users/detail.html` - Added portal settings form
- `templates/admin_panel/users/partials/user_row.html` - Added portal badge

### Created Files
- `apps/portal/__init__.py`
- `apps/portal/apps.py`
- `apps/portal/middleware.py`
- `apps/portal/mixins.py`
- `apps/portal/urls.py`
- `apps/portal/views.py`
- `templates/portal/base_portal.html`
- `templates/portal/home.html`
- `templates/portal/template_select.html`
- `templates/portal/ticket_create.html`
- `templates/portal/ticket_list.html`
- `templates/portal/ticket_detail.html`
- `templates/portal/partials/comment_list.html`
- `templates/portal/partials/attachment_list.html`
- `apps/accounts/migrations/0003_add_portal_client.py`
- `test_issue28_customer_portal.py`

## Summary

The Customer Portal feature has been successfully implemented with all acceptance criteria met. Portal users can now:
1. Log in and be automatically redirected to the portal
2. Select from available templates (global + client-specific)
3. Create tickets with YAML-defined custom fields
4. View and filter their own tickets
5. Add comments and attachments via HTMX
6. Access a minimal, focused interface without internal Friday tools

Staff can manage portal users through the admin panel, toggling portal access and assigning clients as needed. The implementation follows Friday's existing patterns and integrates seamlessly with the mail engine, task templates, and markdown editor systems.
