"""
Core models for Friday project.
"""
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
