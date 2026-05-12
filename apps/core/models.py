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
