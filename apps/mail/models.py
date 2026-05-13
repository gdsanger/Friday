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


class MailHook(models.Model):
    """
    Configures when which mail is sent.
    Staff can activate/deactivate hooks.
    """
    # Available Hook Events
    EVENT_TASK_CREATED = 'task_created'
    EVENT_TASK_ASSIGNED = 'task_assigned'
    EVENT_TASK_DONE = 'task_done'
    EVENT_TASK_COMMENT = 'task_comment'
    EVENT_TASK_OVERDUE = 'task_overdue'  # via Celery Beat
    EVENT_PORTAL_CREATED = 'portal_ticket_created'
    EVENT_PORTAL_DONE = 'portal_ticket_done'
    EVENT_DAILY_DIGEST = 'daily_digest'  # via Celery Beat
    EVENT_USER_INVITED = 'user_invited'

    EVENT_CHOICES = [
        (EVENT_TASK_CREATED, 'Task created'),
        (EVENT_TASK_ASSIGNED, 'Task assigned'),
        (EVENT_TASK_DONE, 'Task completed'),
        (EVENT_TASK_COMMENT, 'Comment added'),
        (EVENT_TASK_OVERDUE, 'Task overdue'),
        (EVENT_PORTAL_CREATED, 'Portal: Ticket received'),
        (EVENT_PORTAL_DONE, 'Portal: Ticket completed'),
        (EVENT_DAILY_DIGEST, 'Daily summary'),
        (EVENT_USER_INVITED, 'User invited'),
    ]

    # Recipient Types
    RECIPIENT_ASSIGNEE = 'assignee'
    RECIPIENT_CREATOR = 'creator'
    RECIPIENT_WATCHERS = 'watchers'
    RECIPIENT_PROJECT_MANAGER = 'project_manager'
    RECIPIENT_PORTAL_USER = 'portal_user'

    RECIPIENT_CHOICES = [
        (RECIPIENT_ASSIGNEE, 'Assigned person/team'),
        (RECIPIENT_CREATOR, 'Creator'),
        (RECIPIENT_WATCHERS, 'Watchers'),
        (RECIPIENT_PROJECT_MANAGER, 'Project manager'),
        (RECIPIENT_PORTAL_USER, 'Portal user (creator)'),
    ]

    event = models.CharField(max_length=50, choices=EVENT_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    recipients = models.JSONField(
        default=list,
        help_text='List of recipient types, e.g. ["assignee", "watchers"]'
    )
    template_name = models.CharField(
        max_length=100,
        help_text='Template filename without .html, e.g. task_assigned'
    )
    subject_template = models.CharField(
        max_length=200,
        help_text='Subject template, e.g. "New task: {task_title}"'
    )
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event']
        verbose_name = 'Mail Hook'
        verbose_name_plural = 'Mail Hooks'

    def __str__(self):
        status = '✓' if self.is_active else '✗'
        return f'[{status}] {self.get_event_display()}'

