# ISSUE-47: Azure AD User Pre-Provisioning - Implementation Summary

## Overview

This feature enables staff members to search for users in Azure AD/Entra ID and pre-provision them in Friday before their first login. The system automatically matches pre-provisioned users via their `azure_oid` during SSO authentication.

## Implementation Details

### 1. Azure Directory Integration (`apps/accounts/azure_directory.py`)

**Functions:**
- `search_azure_users(query, limit=20)` - Search users in Azure AD by name, email, or UPN
- `get_azure_user(azure_oid)` - Fetch single user by Azure Object ID

**Requirements:**
- Uses existing Mail Service Graph API token (Client Credentials Flow)
- Requires `User.Read.All` permission in Azure App Registration
- Searches across: displayName, mail, userPrincipalName
- Returns structured user data: azure_oid, azure_upn, email, name, job_title, department

### 2. URL Routes (`apps/admin_panel/urls.py`)

```python
path('users/invite-azure/', views.UserInviteView.as_view(), name='admin-user-invite-azure')
path('users/invite-azure/search/', views.UserInviteSearchView.as_view(), name='admin-user-invite-search')
path('users/invite-azure/provision/', views.UserProvisionView.as_view(), name='admin-user-provision')
```

### 3. Views (`apps/admin_panel/views.py`)

**UserInviteView**
- Main invitation page
- Provides context: available clients and teams
- Staff-only access via `StaffRequiredMixin`

**UserInviteSearchView**
- HTMX endpoint for live search
- Minimum 2 characters required
- Marks already-provisioned users (via azure_oid lookup)
- Returns partial HTML with search results

**UserProvisionView**
- Processes user provisioning POST requests
- Supports multiple user selection (via checkboxes)
- Configuration options:
  - User type: Friday User or Portal User
  - Portal client (for portal users)
  - Team assignment (for Friday users, multi-select)
  - Send invitation email (checkbox, default: enabled)
- Generates unique usernames from UPN (increments on collision)
- Sets `set_unusable_password()` to enforce SSO-only login
- Creates TeamMembership records
- Dispatches invitation email via Celery

### 4. Templates

**Main Page: `templates/admin_panel/users/invite.html`**
- Search input with HTMX live search (400ms debounce)
- Search indicator with spinner
- Results container for dynamic content

**Search Results: `templates/admin_panel/users/partials/invite_results.html`**
- Results table with checkboxes
- User details: name, email, department, job title
- Status badges: "Verfügbar" or "Bereits in Friday"
- Provisioning form with:
  - User type selector (Friday/Portal)
  - Dynamic fields based on user type
  - Team multi-select (Friday users)
  - Client dropdown (Portal users)
  - Send invitation checkbox
- JavaScript toggle for conditional fields

**Provision Result: `templates/admin_panel/users/partials/provision_result.html`**
- Success alerts with provisioned users list
- Warning for skipped users (already exist)
- Error alerts with detailed messages

### 5. Mail Integration

**Task: `send_invitation_mail(user_id)` in `apps/mail/tasks.py`**
- Uses new mail engine with `dispatch()` function
- Event: `MailHook.EVENT_USER_INVITED`
- Context variables:
  - `recipient_name` - Display name or username
  - `login_url` - Direct link to Azure SSO (`/accounts/azure/login/`)
  - `app_url` - Base site URL
  - `user_type` - "Friday" or "Portal"
  - `portal_client` - Client name (for portal users)

**Template: `templates/mail/user_invited.html`**
- German language welcome message
- Conditional content based on user type
- Info box with access details (SSO, user area)
- Direct SSO login button
- No password reset - enforces SSO-only access

### 6. Navigation Integration

**User List Page: `templates/admin_panel/users/list.html`**
- Added "Azure AD Einladen" button in button group
- Links to `/admin-panel/users/invite-azure/`
- Positioned next to existing "Invite User" modal button

## User Flow

```
1. Staff → Admin Panel → Users → "Azure AD Einladen"
2. Enter search query (min 2 chars)
3. HTMX live search → Results appear
4. Select user(s) via checkboxes
5. Configure:
   - User type (Friday/Portal)
   - Client (if Portal)
   - Teams (if Friday)
   - Email invitation
6. Click "Ausgewählte User einladen"
7. System:
   - Creates User records with azure_oid
   - Sets unusable password
   - Creates team memberships
   - Sends invitation email (Celery)
8. User receives email → Clicks SSO link
9. Azure SSO → azure_oid matches → Auto-login
10. User lands on appropriate dashboard
```

## Database Changes

**No migrations required** - Uses existing User model fields:
- `azure_oid` - Already indexed for lookup
- `azure_upn` - Already available
- `is_portal_user` - Already available
- `portal_client` - Already available

## Testing

**Test File: `apps/accounts/tests/test_azure_provisioning.py`**

Test Coverage:
1. **Azure Directory Tests:**
   - Successful user search
   - Short query rejection (< 2 chars)
   - API error handling
   - Single user fetch by OID

2. **View Tests:**
   - Staff-only access enforcement
   - Invitation page loads correctly
   - Search results display
   - Existing users marked correctly
   - Friday user provisioning
   - Portal user provisioning
   - Duplicate user skipping
   - Username uniqueness generation

3. **Mail Tests:**
   - Friday user invitation email
   - Portal user invitation email (with client name)

## Configuration Requirements

### Azure App Registration

The Mail Service App Registration needs additional permission:

```
Microsoft Graph → Application Permissions:
  ✓ Mail.Send           (existing)
  ✓ User.Read.All       (NEW - required for search)
```

Admin consent required after adding permission.

### Environment Variables

No new environment variables needed - reuses existing mail service config:
- `MAIL_AZURE_CLIENT_ID`
- `MAIL_AZURE_CLIENT_SECRET`
- `MAIL_AZURE_TENANT_ID`
- `SITE_URL` (for invitation link)

## Security Considerations

1. **SSO-Only Access:**
   - Users created with `set_unusable_password()`
   - No password reset functionality
   - Enforces Azure AD authentication

2. **Staff-Only Feature:**
   - All views protected with `StaffRequiredMixin`
   - Only staff can search and provision users

3. **Duplicate Prevention:**
   - Checks `azure_oid` before creation
   - Skips existing users automatically

4. **Username Generation:**
   - Base username from UPN
   - Auto-increments on collision
   - Ensures uniqueness

## Acceptance Criteria

### Azure AD Search
- [x] Search starts at 2 characters (HTMX with 400ms debounce)
- [x] Search finds users by name, email, and UPN
- [x] Spinner appears during search
- [x] Existing users marked as "Bereits in Friday" and disabled
- [x] Not found queries show meaningful message
- [x] Graph API errors caught (no crash)

### Provisioning
- [x] Multiple users selectable via checkbox
- [x] User type: "Friday User" or "Portal User" selectable
- [x] Portal user: Client dropdown appears (required)
- [x] Friday user: Team dropdown appears (optional, multi-select)
- [x] "Send invitation email" checkbox - default active
- [x] User created with azure_oid, azure_upn, email, display_name
- [x] User has `set_unusable_password()` - SSO-only login
- [x] Portal user has `is_portal_user=True` and `portal_client` set
- [x] Team assignment created correctly
- [x] Existing users skipped (no duplicate)
- [x] Result shows: provisioned / skipped / errors

### Invitation Email
- [x] Email sent as Celery task (non-blocking)
- [x] Email contains direct link to `/accounts/azure/login/`
- [x] Email distinguishes between Friday User and Portal User
- [x] Portal user email mentions client name
- [x] No password reset link - SSO only

### First Login
- [x] User clicks email link → Azure SSO
- [x] `azure_oid` matches existing user → no new account
- [x] User lands on appropriate dashboard (Friday/Portal)

## File Checklist

**New Files:**
- [x] `apps/accounts/azure_directory.py` - Azure AD integration
- [x] `templates/admin_panel/users/invite.html` - Main page
- [x] `templates/admin_panel/users/partials/invite_results.html` - Search results
- [x] `templates/admin_panel/users/partials/provision_result.html` - Result feedback
- [x] `apps/accounts/tests/test_azure_provisioning.py` - Comprehensive tests

**Modified Files:**
- [x] `apps/admin_panel/urls.py` - Added 3 new routes
- [x] `apps/admin_panel/views.py` - Added 3 new view classes
- [x] `apps/mail/tasks.py` - Added `send_invitation_mail` task
- [x] `templates/mail/user_invited.html` - Updated for SSO invitation
- [x] `templates/admin_panel/users/list.html` - Added Azure invitation button

## Dependencies

**Reuses Existing:**
- MSAL (Microsoft Authentication Library)
- httpx (HTTP client for Graph API)
- Celery (async task queue)
- django-htmx (HTMX integration)
- Bootstrap 5 (UI framework)

**No new packages required.**

## Performance Considerations

1. **Graph API Search:**
   - 400ms debounce prevents excessive API calls
   - Limits results to 20 users by default
   - 10-second timeout on HTTP requests

2. **User Lookup:**
   - `azure_oid` field is indexed
   - Batch lookup for marking existing users

3. **Email Sending:**
   - Celery task with retry (3x)
   - Non-blocking provisioning flow

## Error Handling

1. **Graph API Failures:**
   - Token acquisition errors logged
   - HTTP errors return empty results (no crash)
   - Timeout protection (10 seconds)

2. **Provisioning Errors:**
   - Individual user failures don't block batch
   - Detailed error messages in result
   - Existing users gracefully skipped

3. **Email Failures:**
   - Celery retry mechanism (3 attempts)
   - User created even if email fails
   - Error logged for admin review

## Future Enhancements

Potential improvements:
1. Bulk import from CSV (with Azure OID column)
2. Group-based provisioning (import entire Azure AD groups)
3. Scheduled sync to deactivate removed Azure users
4. Profile photo sync from Azure AD
5. Manager relationship sync
6. Department-based team auto-assignment

## Documentation

This feature requires updating:
1. Admin documentation (how to invite users)
2. Azure setup guide (User.Read.All permission)
3. Mail hook configuration guide

## Deployment Checklist

Before deploying:
- [ ] Add `User.Read.All` permission to Mail Azure App Registration
- [ ] Grant admin consent in Azure portal
- [ ] Test Graph API search with production credentials
- [ ] Verify MailHook for `user_invited` event is active
- [ ] Test email delivery to external addresses
- [ ] Verify SSO login matches azure_oid correctly

## References

- Issue: ISSUE-47
- Dependencies: ISSUE-03 (Graph API), ISSUE-05 (Azure SSO), ISSUE-34 (Mail Engine)
- Graph API Documentation: https://learn.microsoft.com/en-us/graph/api/user-list
