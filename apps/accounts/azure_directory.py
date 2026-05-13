"""
Azure Directory API integration for user search and lookup.
Uses Microsoft Graph API to search for users in the Azure AD tenant.

REQUIRED AZURE AD PERMISSIONS:
The Azure AD App Registration configured with MAIL_AZURE_CLIENT_ID must have:
- Application Permission: User.Read.All (NOT Delegated permission)
- Admin Consent: Must be granted by a tenant administrator

To grant permissions:
1. Go to Azure Portal → App Registrations → Your App
2. API Permissions → Add permission → Microsoft Graph → Application permissions
3. Select "User.Read.All"
4. Click "Grant admin consent"
"""
import httpx
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


class AzureDirectoryError(Exception):
    """Custom exception for Azure Directory API errors."""
    pass


def search_azure_users(query: str, limit: int = 20) -> list[dict]:
    """
    Search users in Azure AD tenant via Graph API.
    Returns list of user dictionaries.

    Searches in: displayName, mail, userPrincipalName

    Args:
        query: Search query string (minimum 2 characters)
        limit: Maximum number of results to return

    Returns:
        List of user dictionaries with keys:
        - azure_oid: Azure Object ID
        - azure_upn: UserPrincipalName
        - email: Email address
        - name: Display name
        - job_title: Job title
        - department: Department

    Raises:
        AzureDirectoryError: If permissions are insufficient or configuration is invalid
    """
    if not query or len(query) < 2:
        return []

    # Validate configuration
    if not settings.MAIL_AZURE_CLIENT_ID or not settings.MAIL_AZURE_CLIENT_SECRET:
        logger.error(
            'Azure AD configuration incomplete: MAIL_AZURE_CLIENT_ID and '
            'MAIL_AZURE_CLIENT_SECRET must be set in environment variables'
        )
        raise AzureDirectoryError(
            'Azure AD is not properly configured. Please contact your administrator.'
        )

    try:
        from apps.mail.service_new import MailService
        token = MailService._get_token()
    except Exception as e:
        logger.error(f'Failed to get Graph API token: {e}', exc_info=True)
        raise AzureDirectoryError(
            'Failed to authenticate with Azure AD. Please check the application credentials.'
        ) from e

    headers = {
        'Authorization': f'Bearer {token}',
        'ConsistencyLevel': 'eventual',  # Required for $count
    }

    # Graph API $filter - searches across multiple fields
    # Escape single quotes in query to prevent OData syntax errors
    escaped_query = query.replace("'", "''")

    params = {
        '$filter': (
            f"startswith(displayName,'{escaped_query}') or "
            f"startswith(mail,'{escaped_query}') or "
            f"startswith(userPrincipalName,'{escaped_query}')"
        ),
        '$select': 'id,displayName,mail,userPrincipalName,jobTitle,department',
        '$top': str(limit),
        '$orderby': 'displayName',
        '$count': 'true',
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f'{GRAPH_BASE}/users',
                headers=headers,
                params=params,
            )

        if response.status_code == 403:
            error_data = response.json() if response.text else {}
            error_code = error_data.get('error', {}).get('code', 'Unknown')
            error_message = error_data.get('error', {}).get('message', 'Insufficient privileges')

            logger.error(
                f'Graph API permission denied (403): {error_code} - {error_message}\n'
                f'The Azure AD app registration needs Application permission "User.Read.All" '
                f'with admin consent. Current tenant: {settings.MAIL_AZURE_TENANT_ID}, '
                f'Client ID: {settings.MAIL_AZURE_CLIENT_ID[:8]}...'
            )
            raise AzureDirectoryError(
                'Azure AD permission denied. The application needs "User.Read.All" '
                'permission with admin consent. Please contact your administrator.'
            )

        if response.status_code == 401:
            logger.error(
                f'Graph API authentication failed (401). Check that MAIL_AZURE_CLIENT_ID, '
                f'MAIL_AZURE_CLIENT_SECRET, and MAIL_AZURE_TENANT_ID are correct.'
            )
            raise AzureDirectoryError(
                'Azure AD authentication failed. Please check the application credentials.'
            )

        if response.status_code != 200:
            logger.error(
                f'Graph API search failed: {response.status_code} - {response.text[:500]}'
            )
            raise AzureDirectoryError(
                f'Azure AD search failed with status {response.status_code}. '
                'Please try again or contact your administrator.'
            )

        users = response.json().get('value', [])

        return [
            {
                'azure_oid': u.get('id', ''),
                'azure_upn': u.get('userPrincipalName', ''),
                'email': u.get('mail') or u.get('userPrincipalName', ''),
                'name': u.get('displayName', ''),
                'job_title': u.get('jobTitle', ''),
                'department': u.get('department', ''),
            }
            for u in users
            if u.get('id')  # Only users with OID
        ]

    except httpx.HTTPError as e:
        logger.error(f'HTTP error searching Azure users: {e}', exc_info=True)
        raise AzureDirectoryError(
            'Network error while searching Azure AD. Please check your connection.'
        ) from e
    except AzureDirectoryError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        logger.error(f'Unexpected error searching Azure users: {e}', exc_info=True)
        raise AzureDirectoryError(
            'An unexpected error occurred while searching Azure AD.'
        ) from e


def get_azure_user(azure_oid: str) -> dict | None:
    """
    Get single user by OID from Azure AD.

    Args:
        azure_oid: Azure Object ID

    Returns:
        User dictionary or None if not found

    Raises:
        AzureDirectoryError: If permissions are insufficient or configuration is invalid
    """
    # Validate configuration
    if not settings.MAIL_AZURE_CLIENT_ID or not settings.MAIL_AZURE_CLIENT_SECRET:
        logger.error(
            'Azure AD configuration incomplete: MAIL_AZURE_CLIENT_ID and '
            'MAIL_AZURE_CLIENT_SECRET must be set in environment variables'
        )
        raise AzureDirectoryError(
            'Azure AD is not properly configured. Please contact your administrator.'
        )

    try:
        from apps.mail.service_new import MailService
        token = MailService._get_token()
    except Exception as e:
        logger.error(f'Failed to get Graph API token: {e}', exc_info=True)
        raise AzureDirectoryError(
            'Failed to authenticate with Azure AD. Please check the application credentials.'
        ) from e

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f'{GRAPH_BASE}/users/{azure_oid}',
                headers={'Authorization': f'Bearer {token}'},
                params={'$select': 'id,displayName,mail,userPrincipalName,jobTitle,department'},
            )

        if response.status_code == 403:
            error_data = response.json() if response.text else {}
            error_code = error_data.get('error', {}).get('code', 'Unknown')
            error_message = error_data.get('error', {}).get('message', 'Insufficient privileges')

            logger.error(
                f'Graph API permission denied (403) for user {azure_oid}: {error_code} - {error_message}\n'
                f'The Azure AD app registration needs Application permission "User.Read.All" '
                f'with admin consent. Current tenant: {settings.MAIL_AZURE_TENANT_ID}'
            )
            raise AzureDirectoryError(
                'Azure AD permission denied. The application needs "User.Read.All" '
                'permission with admin consent. Please contact your administrator.'
            )

        if response.status_code == 401:
            logger.error(
                f'Graph API authentication failed (401) for user {azure_oid}. '
                f'Check that MAIL_AZURE_CLIENT_ID, MAIL_AZURE_CLIENT_SECRET, and '
                f'MAIL_AZURE_TENANT_ID are correct.'
            )
            raise AzureDirectoryError(
                'Azure AD authentication failed. Please check the application credentials.'
            )

        if response.status_code == 404:
            logger.warning(f'Azure user not found: {azure_oid}')
            return None

        if response.status_code != 200:
            logger.error(
                f'Graph API get user failed: {response.status_code} - {response.text[:500]}'
            )
            raise AzureDirectoryError(
                f'Azure AD request failed with status {response.status_code}. '
                'Please try again or contact your administrator.'
            )

        u = response.json()
        return {
            'azure_oid': u.get('id', ''),
            'azure_upn': u.get('userPrincipalName', ''),
            'email': u.get('mail') or u.get('userPrincipalName', ''),
            'name': u.get('displayName', ''),
            'job_title': u.get('jobTitle', ''),
            'department': u.get('department', ''),
        }

    except httpx.HTTPError as e:
        logger.error(f'HTTP error getting Azure user {azure_oid}: {e}', exc_info=True)
        raise AzureDirectoryError(
            'Network error while accessing Azure AD. Please check your connection.'
        ) from e
    except AzureDirectoryError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        logger.error(f'Unexpected error getting Azure user {azure_oid}: {e}', exc_info=True)
        raise AzureDirectoryError(
            'An unexpected error occurred while accessing Azure AD.'
        ) from e
