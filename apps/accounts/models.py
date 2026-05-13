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

    # Azure Entra ID / SSO
    azure_oid = models.CharField(max_length=100, blank=True, db_index=True)  # object ID from token
    azure_upn = models.EmailField(blank=True)  # UserPrincipalName

    # Preferences
    notify_email = models.BooleanField(default=True)
    notify_inapp = models.BooleanField(default=True)
    timezone = models.CharField(max_length=50, default='Europe/Berlin')

    # Portal access
    is_portal_user = models.BooleanField(
        default=False,
        help_text='Portal users have limited access and are not shown in assignee dropdowns'
    )
    portal_client = models.ForeignKey(
        'core.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='portal_users',
        help_text='Client/Mandant assignment for portal users'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        """Return display name, full name, or username."""
        return self.display_name or self.get_full_name() or self.username

    @property
    def teams(self):
        """Get all teams this user belongs to."""
        from apps.teams.models import Team
        return Team.objects.filter(memberships__user=self, is_active=True)

    @property
    def initials(self):
        """Return user initials from their name."""
        parts = self.full_name.split()
        return ''.join(p[0].upper() for p in parts[:2]) if parts else '?'

    @property
    def is_team_lead(self):
        """Check if user has any team membership with role='lead'."""
        return self.team_memberships.filter(role='lead').exists()
