"""
Mail service for Friday project - Microsoft Graph API with Client Credentials Flow.

This is the NEW implementation for ISSUE-34.
Uses a separate Azure App Registration with Client Credentials (no user token).
Sends all mail from a shared system mailbox.

REQUIRED AZURE AD PERMISSIONS:
The Azure AD App Registration configured with MAIL_AZURE_CLIENT_ID must have:
- Application Permission: Mail.Send (to send emails)
- Application Permission: Mail.ReadWrite (to read/write emails)
- Application Permission: User.Read.All (to search and read user information)
- Admin Consent: Must be granted by a tenant administrator

To grant permissions:
1. Go to Azure Portal → App Registrations → Your App
2. API Permissions → Add permission → Microsoft Graph → Application permissions
3. Select "Mail.Send", "Mail.ReadWrite", and "User.Read.All"
4. Click "Grant admin consent"
"""
import httpx
from msal import ConfidentialClientApplication
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
TOKEN_CACHE_KEY = 'mail_service_access_token'


class MailServiceError(Exception):
    """Exception raised when Mail Service operations fail."""
    pass


class MailService:
    """
    System-wide Mail Service using Microsoft Graph API.
    Uses Client Credentials Flow — no user token needed.
    Sends always from the configured system mailbox.
    """

    # ── Token Management (Client Credentials) ────────────────────

    @classmethod
    def _get_token(cls) -> str:
        """
        Get an app token via Client Credentials Flow.
        Token is cached for 55 minutes (valid for 60 min).

        Raises:
            MailServiceError: If token acquisition fails due to config or permission issues
        """
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        # Validate configuration
        if not settings.MAIL_AZURE_CLIENT_ID:
            logger.error('MAIL_AZURE_CLIENT_ID is not configured')
            raise MailServiceError(
                'Azure AD Mail Service is not configured: MAIL_AZURE_CLIENT_ID is missing. '
                'Please set the environment variable.'
            )

        if not settings.MAIL_AZURE_CLIENT_SECRET:
            logger.error('MAIL_AZURE_CLIENT_SECRET is not configured')
            raise MailServiceError(
                'Azure AD Mail Service is not configured: MAIL_AZURE_CLIENT_SECRET is missing. '
                'Please set the environment variable.'
            )

        if not settings.MAIL_AZURE_TENANT_ID:
            logger.error('MAIL_AZURE_TENANT_ID is not configured')
            raise MailServiceError(
                'Azure AD Mail Service is not configured: MAIL_AZURE_TENANT_ID is missing. '
                'Please set the environment variable.'
            )

        try:
            app = ConfidentialClientApplication(
                client_id=settings.MAIL_AZURE_CLIENT_ID,
                client_credential=settings.MAIL_AZURE_CLIENT_SECRET,
                authority=f'https://login.microsoftonline.com/{settings.MAIL_AZURE_TENANT_ID}',
            )
            result = app.acquire_token_for_client(
                scopes=['https://graph.microsoft.com/.default']
            )
        except Exception as e:
            logger.error(f'Failed to create MSAL app or acquire token: {e}', exc_info=True)
            raise MailServiceError(
                f'Failed to authenticate with Azure AD: {str(e)}'
            ) from e

        if 'access_token' not in result:
            error = result.get('error', 'unknown_error')
            error_description = result.get('error_description', 'No description provided')
            error_codes = result.get('error_codes', [])

            logger.error(
                f'Token acquisition failed: {error}\n'
                f'Description: {error_description}\n'
                f'Error codes: {error_codes}\n'
                f'Tenant: {settings.MAIL_AZURE_TENANT_ID}, '
                f'Client ID: {settings.MAIL_AZURE_CLIENT_ID[:8]}...'
            )

            # Provide helpful error messages based on error type
            if error == 'invalid_client':
                raise MailServiceError(
                    'Azure AD authentication failed: Invalid client credentials. '
                    'Please verify MAIL_AZURE_CLIENT_ID and MAIL_AZURE_CLIENT_SECRET are correct.'
                )
            elif error == 'unauthorized_client':
                raise MailServiceError(
                    'Azure AD authentication failed: The client is not authorized. '
                    'Please ensure the app registration has the correct permissions '
                    '(Mail.Send, Mail.ReadWrite, User.Read.All) with admin consent.'
                )
            else:
                raise MailServiceError(
                    f'Azure AD token acquisition failed: {error} - {error_description}'
                )

        token = result['access_token']
        cache.set(TOKEN_CACHE_KEY, token, timeout=55 * 60)
        logger.info('Successfully acquired Azure AD token for Mail Service')
        return token

    @classmethod
    def _headers(cls) -> dict:
        """Return headers for Graph API requests."""
        return {
            'Authorization': f'Bearer {cls._get_token()}',
            'Content-Type': 'application/json',
        }

    # ── Mail Sending ───────────────────────────────────────────────

    @classmethod
    def send(
        cls,
        to: list[str],
        subject: str,
        body_html: str,
        cc: list[str] | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """
        Send a mail from the system mailbox.
        Returns True if successful.
        """
        recipients = [{'emailAddress': {'address': a}} for a in to]
        cc_list = [{'emailAddress': {'address': a}} for a in (cc or [])]

        message = {
            'subject': subject,
            'body': {
                'contentType': 'HTML',
                'content': body_html,
            },
            'toRecipients': recipients,
            'from': {
                'emailAddress': {
                    'address': settings.MAIL_FROM_ADDRESS,
                    'name': settings.MAIL_FROM_NAME,
                }
            },
        }

        if cc_list:
            message['ccRecipients'] = cc_list

        if reply_to:
            message['replyTo'] = [{'emailAddress': {'address': reply_to}}]

        mailbox = settings.MAIL_SHARED_MAILBOX

        with httpx.Client(timeout=15) as client:
            response = client.post(
                f'{GRAPH_BASE}/users/{mailbox}/sendMail',
                headers=cls._headers(),
                json={'message': message, 'saveToSentItems': True},
            )

        if response.status_code == 202:
            return True

        raise MailServiceError(
            f'Graph API error {response.status_code}: {response.text[:200]}'
        )

    @classmethod
    def send_template(
        cls,
        to: list[str],
        template_name: str,
        context: dict,
        subject: str,
        cc: list[str] | None = None,
    ) -> bool:
        """
        Render an HTML template and send it.
        template_name: Filename without path, e.g. 'task_assigned'
        """
        from apps.mail.templates import render_mail_template
        body_html = render_mail_template(template_name, context)
        return cls.send(to=to, subject=subject, body_html=body_html, cc=cc)
