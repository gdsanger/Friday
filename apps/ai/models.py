"""
AI models for Friday project.
"""
from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class AIProviderConfig(models.Model):
    """AI Provider configuration model."""
    PROVIDER_OPENAI  = 'openai'
    PROVIDER_CLAUDE  = 'claude'
    PROVIDER_CHOICES = [
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_CLAUDE, 'Anthropic Claude'),
    ]
    provider       = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        unique=True
    )
    api_key        = EncryptedCharField(max_length=200)
    model_name     = models.CharField(max_length=100)
    fallback_model = models.CharField(max_length=100, blank=True)
    is_active      = models.BooleanField(default=True)
    rpm_limit      = models.IntegerField(default=60)
    tpm_limit      = models.IntegerField(default=100_000)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Provider Config'
        verbose_name_plural = 'AI Provider Configs'

    def __str__(self):
        return f'{self.get_provider_display()} - {self.model_name}'


class AIGlobalSettings(models.Model):
    """Singleton — pk always 1."""
    default_provider        = models.CharField(max_length=20, default='openai')
    fallback_provider       = models.CharField(max_length=20, blank=True)
    monthly_token_budget    = models.BigIntegerField(default=10_000_000)
    per_user_daily_limit    = models.IntegerField(default=50_000)
    is_enabled              = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'AI Global Settings'
        verbose_name_plural = 'AI Global Settings'

    def __str__(self):
        return 'AI Global Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AIUsageLog(models.Model):
    """Log of AI API usage."""
    user              = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    team              = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    provider          = models.CharField(max_length=20)
    action            = models.CharField(max_length=50)
    prompt_tokens     = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens      = models.IntegerField(default=0)
    duration_ms       = models.IntegerField(default=0)
    success           = models.BooleanField(default=True)
    error_message     = models.TextField(blank=True)
    object_type       = models.CharField(max_length=50, blank=True)
    object_id         = models.CharField(max_length=50, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Usage Log'
        verbose_name_plural = 'AI Usage Logs'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['team', 'created_at']),
        ]

    def __str__(self):
        return f'{self.provider} - {self.action} ({self.created_at})'
