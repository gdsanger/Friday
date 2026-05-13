"""
Azure Directory API integration for user search and lookup.
Uses Microsoft Graph API to search for users in the Azure AD tenant.
"""
import httpx
import logging

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


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
    """
    if not query or len(query) < 2:
        return []

    try:
        from apps.mail.service_new import MailService
        token = MailService._get_token()
    except Exception as e:
        logger.error(f'Failed to get Graph API token: {e}')
        return []

    headers = {
        'Authorization': f'Bearer {token}',
        'ConsistencyLevel': 'eventual',  # Required for $search
    }

    # Graph API $search - searches across multiple fields
    search_query = f'"{query}"'
    params = {
        '$search': f'displayName:{search_query} OR mail:{search_query} OR userPrincipalName:{search_query}',
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

        if response.status_code != 200:
            logger.error(f'Graph API search failed: {response.status_code} - {response.text[:200]}')
            return []

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

    except Exception as e:
        logger.error(f'Error searching Azure users: {e}')
        return []


def get_azure_user(azure_oid: str) -> dict | None:
    """
    Get single user by OID from Azure AD.

    Args:
        azure_oid: Azure Object ID

    Returns:
        User dictionary or None if not found
    """
    try:
        from apps.mail.service_new import MailService
        token = MailService._get_token()
    except Exception as e:
        logger.error(f'Failed to get Graph API token: {e}')
        return None

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f'{GRAPH_BASE}/users/{azure_oid}',
                headers={'Authorization': f'Bearer {token}'},
                params={'$select': 'id,displayName,mail,userPrincipalName,jobTitle,department'},
            )

        if response.status_code != 200:
            logger.error(f'Graph API get user failed: {response.status_code}')
            return None

        u = response.json()
        return {
            'azure_oid': u.get('id', ''),
            'azure_upn': u.get('userPrincipalName', ''),
            'email': u.get('mail') or u.get('userPrincipalName', ''),
            'name': u.get('displayName', ''),
            'job_title': u.get('jobTitle', ''),
            'department': u.get('department', ''),
        }

    except Exception as e:
        logger.error(f'Error getting Azure user {azure_oid}: {e}')
        return None
