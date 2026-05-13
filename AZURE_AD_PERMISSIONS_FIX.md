# Azure AD User Search Permission Fix

## Problem
The Azure AD user search was failing with a 403 "Authorization_RequestDenied" error:
```
Graph API search failed: 403 - {"error":{"code":"Authorization_RequestDenied","message":"Insufficient privileges to complete the operation."}}
```

## Root Cause
The Azure AD App Registration configured with the `MAIL_AZURE_CLIENT_ID` credentials did not have the correct **Application permissions** with admin consent granted.

## Solution

### 1. Required Azure AD Permissions
The Azure AD App Registration must have the following **Application permissions** (NOT Delegated permissions):
- `User.Read.All` - To search and read user information
- `Mail.Send` - To send emails
- `Mail.ReadWrite` - To read/write emails

### 2. How to Grant Permissions

1. **Navigate to Azure Portal**
   - Go to https://portal.azure.com
   - Navigate to: Azure Active Directory → App Registrations
   - Find and select your app (the one with Client ID from `MAIL_AZURE_CLIENT_ID`)

2. **Add API Permissions**
   - Click "API permissions" in the left sidebar
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Application permissions" (NOT Delegated)
   - Search for and select:
     - `User.Read.All`
     - `Mail.Send`
     - `Mail.ReadWrite`
   - Click "Add permissions"

3. **Grant Admin Consent**
   - **IMPORTANT**: After adding permissions, click the "Grant admin consent for [Your Organization]" button
   - Confirm the consent
   - Wait for the status to show "Granted for [Your Organization]" with a green checkmark

### 3. Verify Configuration

Ensure the following environment variables are set correctly:
```bash
MAIL_AZURE_CLIENT_ID=<your-app-client-id>
MAIL_AZURE_CLIENT_SECRET=<your-app-client-secret>
MAIL_AZURE_TENANT_ID=<your-tenant-id>
```

**Note**: These are different from the SSO credentials (`AZURE_CLIENT_ID`, etc.). The mail service uses a separate App Registration with Client Credentials flow.

### 4. Code Improvements Made

#### Enhanced Error Handling
- Added `AzureDirectoryError` exception class for Azure AD-specific errors
- Specific error handling for 403 (permission denied), 401 (auth failed), and other status codes
- Detailed logging with tenant and client ID information for debugging

#### Better Error Messages
- User-friendly error messages in the UI explaining permission issues
- Clear instructions in log messages about what permissions are needed
- Configuration validation that checks if environment variables are set

#### Documentation
- Added comprehensive comments in code explaining required permissions
- Step-by-step instructions for granting permissions in Azure Portal
- Clear distinction between Application and Delegated permissions

#### Testing
- Added tests for 403 error handling
- Added tests for 401 authentication failures
- Added tests for missing configuration
- Added test for view error handling

### 5. Files Modified

1. **apps/accounts/azure_directory.py**
   - Added `AzureDirectoryError` exception class
   - Enhanced error handling in `search_azure_users()`
   - Enhanced error handling in `get_azure_user()`
   - Added configuration validation
   - Added detailed permission documentation in docstrings

2. **apps/mail/service_new.py**
   - Enhanced `_get_token()` with better error messages
   - Added configuration validation
   - Added detailed logging for token acquisition failures
   - Added permission documentation in module docstring

3. **apps/admin_panel/views.py**
   - Updated `UserInviteSearchView` to catch and display `AzureDirectoryError`
   - Updated `UserProvisionView` to catch and display `AzureDirectoryError`

4. **templates/admin_panel/users/partials/invite_results.html**
   - Added error display section with Bootstrap alert styling

5. **apps/accounts/tests/test_azure_provisioning.py**
   - Added test for 403 permission denied error
   - Added test for 401 authentication failure
   - Added test for missing configuration
   - Added test for view error handling

## Testing

After granting the permissions, test the Azure AD user search:

1. Log in to Friday as a staff user
2. Navigate to: Admin Panel → Users → "Azure AD Einladen" button
3. Search for a user (e.g., "Angermeier")
4. The search should now work without 403 errors

## Troubleshooting

### Still Getting 403 Errors?
- Verify admin consent was granted (green checkmark in Azure Portal)
- Check that you're configuring the correct app (match Client ID)
- Ensure you selected "Application permissions" not "Delegated permissions"
- Wait a few minutes after granting consent for changes to propagate

### Getting 401 Errors?
- Verify `MAIL_AZURE_CLIENT_ID` and `MAIL_AZURE_CLIENT_SECRET` are correct
- Verify `MAIL_AZURE_TENANT_ID` matches your Azure AD tenant
- Check that the client secret hasn't expired

### Configuration Issues?
- Check server logs for detailed error messages
- Error messages will now indicate exactly which environment variable is missing
- Use the Django shell to verify settings are loaded correctly:
  ```python
  from django.conf import settings
  print(settings.MAIL_AZURE_CLIENT_ID)
  print(settings.MAIL_AZURE_TENANT_ID)
  ```

## References

- [Microsoft Graph API Permissions Reference](https://docs.microsoft.com/en-us/graph/permissions-reference)
- [Application vs Delegated Permissions](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent)
- [Client Credentials Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-client-creds-grant-flow)
