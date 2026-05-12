"""
Team models for Friday project.
"""
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class Team(TimeStampedModel):
    """Team model for organizing users."""
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color       = models.CharField(max_length=7, default='#6366f1')
    icon        = models.CharField(max_length=50, blank=True)  # Bootstrap icon name
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_members(self):
        """Get all users who are members of this team."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(team_memberships__team=self)


class TeamMembership(TimeStampedModel):
    """Through model for Team-User relationship."""
    ROLE_LEAD   = 'lead'
    ROLE_MEMBER = 'member'
    ROLE_GUEST  = 'guest'
    ROLE_CHOICES = [
        (ROLE_LEAD,   'Team Lead'),
        (ROLE_MEMBER, 'Member'),
        (ROLE_GUEST,  'Guest'),
    ]
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    team      = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role      = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'team')
        verbose_name = 'Team Membership'
        verbose_name_plural = 'Team Memberships'

    def __str__(self):
        return f'{self.user.username} - {self.team.name} ({self.role})'
