"""
Notification models for Friday project.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    """Notification model for in-app notifications."""
    recipient  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    verb       = models.CharField(max_length=100)
    actor      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='triggered_notifications'
    )
    target_ct  = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    target_id  = models.PositiveIntegerField()
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'System'
        return f'{actor_name} {self.verb} - {self.recipient.username}'
