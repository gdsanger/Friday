"""
Mail models for Friday project.
"""
from datetime import timedelta
from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedTextField
from apps.core.models import TimeStampedModel


class UserMailToken(models.Model):
    """
    Stores the Graph API OAuth tokens per user.
    Tokens are encrypted at rest.
    Refreshed automatically by MailService before each call.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mail_token'
    )
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    expires_at = models.DateTimeField()
    scopes = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        """Check if token is expired or expiring within 5 minutes."""
        from django.utils import timezone
        return timezone.now() >= self.expires_at - timedelta(minutes=5)

    def __str__(self):
        return f'Mail Token for {self.user.username}'

    class Meta:
        verbose_name = 'User Mail Token'
        verbose_name_plural = 'User Mail Tokens'


class MailThread(TimeStampedModel):
    """Links an email thread (Graph conversation ID) to a Task."""
    DIRECTION_IN = 'in'
    DIRECTION_OUT = 'out'
    DIRECTION_CHOICES = [
        (DIRECTION_IN, 'Incoming'),
        (DIRECTION_OUT, 'Outgoing'),
    ]

    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='mail_threads'
    )
    graph_message_id = models.CharField(max_length=200, unique=True)
    graph_conversation_id = models.CharField(max_length=200, blank=True, db_index=True)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    subject = models.CharField(max_length=500)
    sender_email = models.EmailField(blank=True)
    sender_name = models.CharField(max_length=200, blank=True)
    body_preview = models.TextField(blank=True)  # first 500 chars
    received_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.direction.upper()}: {self.subject[:50]}'

    class Meta:
        verbose_name = 'Mail Thread'
        verbose_name_plural = 'Mail Threads'
        ordering = ['-created_at']


class WebhookSubscription(TimeStampedModel):
    """Tracks active Graph API notification subscriptions."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webhook_subscriptions'
    )
    subscription_id = models.CharField(max_length=200, unique=True)
    resource = models.CharField(max_length=300)
    expiration = models.DateTimeField()
    client_state = models.CharField(max_length=100)

    def __str__(self):
        return f'Webhook for {self.user.username} (expires {self.expiration})'

    class Meta:
        verbose_name = 'Webhook Subscription'
        verbose_name_plural = 'Webhook Subscriptions'
        ordering = ['-created_at']
