"""
Mail service for Friday project - Microsoft Graph API integration.
"""
import httpx
import secrets
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from .models import UserMailToken, MailThread, WebhookSubscription


GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


class GraphAuthError(Exception):
    """Exception raised when Graph API authentication fails."""
    pass


class MailService:
    """
    All Graph API mail operations.
    Always instantiate with a user: MailService(user=request.user)
    """

    def __init__(self, user):
        self.user = user

    # ── Token Management ─────────────────────────────────────

    def get_valid_token(self) -> str:
        """Return a valid access token, refreshing via MSAL if expired."""
        try:
            token_obj = self.user.mail_token  # raises RelatedObjectDoesNotExist if not connected
        except UserMailToken.DoesNotExist:
            raise GraphAuthError('User has no mail token configured')

        if token_obj.is_expired():
            token_obj = self._refresh_token(token_obj)
        return token_obj.access_token

    def _refresh_token(self, token_obj) -> UserMailToken:
        """Refresh the access token using MSAL."""
        from msal import ConfidentialClientApplication

        app = ConfidentialClientApplication(
            client_id=settings.AZURE_CLIENT_ID,
            client_credential=settings.AZURE_CLIENT_SECRET,
            authority=f'https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}',
        )
        result = app.acquire_token_by_refresh_token(
            token_obj.refresh_token,
            scopes=settings.MSAL_SCOPES,
        )
        if 'access_token' not in result:
            raise GraphAuthError(result.get('error_description', 'Token refresh failed'))

        token_obj.access_token = result['access_token']
        token_obj.refresh_token = result.get('refresh_token', token_obj.refresh_token)
        token_obj.expires_at = timezone.now() + timedelta(seconds=result['expires_in'])
        token_obj.save()
        return token_obj

    def _headers(self) -> dict:
        """Return headers for Graph API requests."""
        return {
            'Authorization': f'Bearer {self.get_valid_token()}',
            'Content-Type': 'application/json',
        }

    # ── Outgoing Mail ─────────────────────────────────────────

    def send_mail(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        task=None,
        save_to_sent: bool = True,
    ) -> str:
        """
        Send an email via Graph API /me/sendMail.
        Returns the Graph message ID.
        Optionally links to a Task by creating a MailThread record.
        """
        payload = {
            'message': {
                'subject': subject,
                'body': {'contentType': 'HTML', 'content': body_html},
                'toRecipients': [
                    {'emailAddress': {'address': addr}} for addr in to
                ],
            },
            'saveToSentItems': save_to_sent,
        }
        with httpx.Client() as client:
            response = client.post(
                f'{GRAPH_BASE}/me/sendMail',
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
            response.raise_for_status()

        if task:
            # Fetch the sent message to get its ID
            msg_id = self._get_last_sent_message_id()
            if msg_id:
                MailThread.objects.create(
                    task=task,
                    graph_message_id=msg_id,
                    direction=MailThread.DIRECTION_OUT,
                    subject=subject,
                    sender_email=self.user.email,
                    sender_name=self.user.full_name,
                )
            return msg_id
        return ''

    def send_notification_mail(self, recipient_user, subject: str, body_html: str):
        """
        Send a system notification email on behalf of the platform.
        Uses the calling user's Graph token but sends to another user.
        """
        self.send_mail(to=[recipient_user.email], subject=subject, body_html=body_html)

    # ── Incoming Mail / Webhook ───────────────────────────────

    def create_webhook_subscription(self) -> WebhookSubscription:
        """
        Subscribe to inbox notifications for this user via Graph API.
        Subscription expires after 3 days — celery-beat renews daily.
        """
        client_state = secrets.token_hex(16)
        expiry = timezone.now() + timedelta(days=3)

        payload = {
            'changeType': 'created',
            'notificationUrl': settings.GRAPH_WEBHOOK_URL,
            'resource': "me/mailFolders('Inbox')/messages",
            'expirationDateTime': expiry.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'clientState': client_state,
        }
        with httpx.Client() as client:
            r = client.post(
                f'{GRAPH_BASE}/subscriptions',
                headers=self._headers(),
                json=payload,
                timeout=15
            )
            r.raise_for_status()
            data = r.json()

        return WebhookSubscription.objects.create(
            user=self.user,
            subscription_id=data['id'],
            resource=data['resource'],
            expiration=expiry,
            client_state=client_state,
        )

    def fetch_message(self, message_id: str) -> dict:
        """Fetch full message body from Graph API."""
        with httpx.Client() as client:
            r = client.get(
                f'{GRAPH_BASE}/me/messages/{message_id}',
                headers=self._headers(),
                params={'$select': 'id,subject,body,sender,conversationId,receivedDateTime'},
                timeout=15,
            )
            r.raise_for_status()
            return r.json()

    # ── Helpers ───────────────────────────────────────────────

    def _get_last_sent_message_id(self) -> str:
        """Get the ID of the most recently sent message."""
        with httpx.Client() as client:
            r = client.get(
                f'{GRAPH_BASE}/me/mailFolders/SentItems/messages',
                headers=self._headers(),
                params={'$top': 1, '$orderby': 'sentDateTime desc', '$select': 'id'},
                timeout=10,
            )
            r.raise_for_status()
            messages = r.json().get('value', [])
            return messages[0]['id'] if messages else ''
