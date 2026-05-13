"""
Mail service for Friday project - Microsoft Graph API with Client Credentials Flow.

This is the NEW implementation for ISSUE-34.
Uses a separate Azure App Registration with Client Credentials (no user token).
Sends all mail from a shared system mailbox.
"""
import httpx
from msal import ConfidentialClientApplication
from django.conf import settings
from django.core.cache import cache


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
        """
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        app = ConfidentialClientApplication(
            client_id=settings.MAIL_AZURE_CLIENT_ID,
            client_credential=settings.MAIL_AZURE_CLIENT_SECRET,
            authority=f'https://login.microsoftonline.com/{settings.MAIL_AZURE_TENANT_ID}',
        )
        result = app.acquire_token_for_client(
            scopes=['https://graph.microsoft.com/.default']
        )

        if 'access_token' not in result:
            raise MailServiceError(
                f"Token error: {result.get('error_description', 'Unknown error')}"
            )

        token = result['access_token']
        cache.set(TOKEN_CACHE_KEY, token, timeout=55 * 60)
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
