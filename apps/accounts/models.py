"""
Custom User model for Friday project.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended Django User model."""

    avatar = models.ImageField(upload_to='avatars/', blank=True)
    display_name = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    # Azure SSO
    azure_oid = models.CharField(max_length=100, blank=True, unique=True, null=True)
    azure_upn = models.EmailField(blank=True)

    # Preferences
    notify_email = models.BooleanField(default=True)
    notify_inapp = models.BooleanField(default=True)
    theme = models.CharField(
        max_length=10,
        default='light',
        choices=[('light', 'Light'), ('dark', 'Dark')]
    )
    timezone = models.CharField(max_length=50, default='Europe/Berlin')

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    @property
    def teams(self):
        """Get all teams this user belongs to."""
        from apps.teams.models import Team
        return Team.objects.filter(memberships__user=self)

    @property
    def full_name(self):
        """Return display name, full name, or username."""
        return self.display_name or self.get_full_name() or self.username
