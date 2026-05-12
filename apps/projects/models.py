"""
Project models for Friday project.
"""
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class Project(TimeStampedModel):
    """Project model for organizing work."""
    STATUS_PLANNING  = 'planning'
    STATUS_ACTIVE    = 'active'
    STATUS_ON_HOLD   = 'on_hold'
    STATUS_DONE      = 'done'
    STATUS_ARCHIVED  = 'archived'
    STATUS_CHOICES = [
        (STATUS_PLANNING, 'Planning'),
        (STATUS_ACTIVE,   'Active'),
        (STATUS_ON_HOLD,  'On Hold'),
        (STATUS_DONE,     'Done'),
        (STATUS_ARCHIVED, 'Archived'),
    ]
    VISIBILITY_MEMBERS = 'members'
    VISIBILITY_ORG     = 'organisation'
    VISIBILITY_CHOICES = [
        (VISIBILITY_MEMBERS, 'Members only'),
        (VISIBILITY_ORG,     'Entire organisation'),
    ]

    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNING
    )
    visibility  = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_MEMBERS
    )
    owner       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_projects'
    )
    start_date  = models.DateField(null=True, blank=True)
    due_date    = models.DateField(null=True, blank=True)
    priority    = models.IntegerField(default=0)
    color       = models.CharField(max_length=7, default='#3b82f6')

    # Members: direct users OR whole teams
    user_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectUserMembership',
        related_name='member_projects',
        blank=True,
    )
    team_members = models.ManyToManyField(
        'teams.Team',
        through='ProjectTeamMembership',
        related_name='member_projects',
        blank=True,
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def get_all_members(self):
        """All effective members: direct users UNION all users from member teams."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        direct   = User.objects.filter(projectusermembership__project=self)
        via_team = User.objects.filter(
            team_memberships__team__projectteammembership__project=self
        )
        return (direct | via_team).distinct()

    def is_member(self, user):
        """Check if user is a member of this project."""
        return self.get_all_members().filter(pk=user.pk).exists()

    def get_effective_role(self, user):
        """Return highest role the user holds in this project."""
        direct = self.projectusermembership_set.filter(user=user).first()
        if direct:
            return direct.role
        team_membership = self.projectteammembership_set.filter(
            team__memberships__user=user
        ).first()
        if team_membership:
            return team_membership.role
        return None


class ProjectUserMembership(models.Model):
    """Through model for Project-User direct membership."""
    ROLE_MANAGER     = 'manager'
    ROLE_CONTRIBUTOR = 'contributor'
    ROLE_VIEWER      = 'viewer'
    ROLE_CHOICES = [
        (ROLE_MANAGER,     'Project Manager'),
        (ROLE_CONTRIBUTOR, 'Contributor'),
        (ROLE_VIEWER,      'Viewer'),
    ]
    project   = models.ForeignKey(Project, on_delete=models.CASCADE)
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role      = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CONTRIBUTOR
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = 'Project User Membership'
        verbose_name_plural = 'Project User Memberships'

    def __str__(self):
        return f'{self.user.username} - {self.project.name} ({self.role})'


class ProjectTeamMembership(models.Model):
    """Through model for Project-Team membership."""
    ROLE_CONTRIBUTOR = 'contributor'
    ROLE_VIEWER      = 'viewer'
    ROLE_CHOICES = [
        (ROLE_CONTRIBUTOR, 'Contributor'),
        (ROLE_VIEWER,      'Viewer'),
    ]
    project  = models.ForeignKey(Project, on_delete=models.CASCADE)
    team     = models.ForeignKey('teams.Team', on_delete=models.CASCADE)
    role     = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CONTRIBUTOR
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'team')
        verbose_name = 'Project Team Membership'
        verbose_name_plural = 'Project Team Memberships'

    def __str__(self):
        return f'{self.team.name} - {self.project.name} ({self.role})'
