"""
Core models for Friday project.
"""
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base: created_at + updated_at on every model."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organisation(TimeStampedModel):
    """
    Single instance representing EOE (the parent organisation).
    pk is always 1. Never create a second instance.
    """
    name        = models.CharField(max_length=200, default='EOE')
    slug        = models.SlugField(unique=True, default='eoe')
    logo        = models.ImageField(upload_to='org/', blank=True)
    description = models.TextField(blank=True)
    website     = models.URLField(blank=True)

    class Meta:
        verbose_name = 'Organisation'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Client(TimeStampedModel):
    """
    A client / Mandant (e.g. HAM, DHGS, HSSH, Seeburg).
    Clients are organisation-wide — not team-specific.
    Only staff can create/edit clients.
    """
    name        = models.CharField(max_length=200, unique=True)
    slug        = models.SlugField(unique=True)
    short_name  = models.CharField(
        max_length=20,
        blank=True,
        help_text='Abbreviation, e.g. HAM, DHGS'
    )
    description = models.TextField(blank=True)
    color       = models.CharField(max_length=7, default='#6366f1')
    logo        = models.ImageField(upload_to='clients/', blank=True)
    is_active   = models.BooleanField(default=True)
    website     = models.URLField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        return self.short_name or self.name


class CapacityBudget(models.Model):
    """
    Weekly Story Point budget for a client/team combination.
    Defines how many SP a team can deliver for a client per week.
    """
    client = models.ForeignKey(
        'core.Client',
        on_delete=models.CASCADE,
        related_name='capacity_budgets'
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='capacity_budgets'
    )
    weekly_sp_budget = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        help_text='Available Story Points per week for this client/team.'
    )
    valid_from = models.DateField(
        help_text='Budget valid from this date (inclusive).'
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text='Budget valid until this date. Null = ongoing.'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['client__name', 'team__name', '-valid_from']
        verbose_name = 'Capacity Budget'
        verbose_name_plural = 'Capacity Budgets'

    def __str__(self):
        return f'{self.client} / {self.team}: {self.weekly_sp_budget} SP/Woche'

    @classmethod
    def current_budget(cls, client, team, date=None):
        """Return the active budget for client/team on given date."""
        from django.utils import timezone
        date = date or timezone.now().date()
        return cls.objects.filter(
            client=client,
            team=team,
            valid_from__lte=date,
        ).filter(
            models.Q(valid_until__isnull=True) |
            models.Q(valid_until__gte=date)
        ).order_by('-valid_from').first()
