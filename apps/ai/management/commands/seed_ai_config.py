"""
Management command to seed AI configuration from environment variables.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.ai.models import AIProviderConfig, AIGlobalSettings


class Command(BaseCommand):
    """Seed AI configuration from environment variables."""
    help = 'Seed AI configuration from environment variables'

    def handle(self, *args, **options):
        """
        This command reads AI configuration from environment variables
        and stores them in the database (encrypted).
        """
        created_count = 0
        updated_count = 0

        # Create/update OpenAI provider config
        if settings.OPENAI_API_KEY:
            openai_config, created = AIProviderConfig.objects.update_or_create(
                provider=AIProviderConfig.PROVIDER_OPENAI,
                defaults={
                    'api_key': settings.OPENAI_API_KEY,
                    'model_name': settings.OPENAI_MODEL,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created OpenAI config with model {settings.OPENAI_MODEL}'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Updated OpenAI config with model {settings.OPENAI_MODEL}'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                '⚠ OPENAI_API_KEY not found in environment, skipping OpenAI config'
            ))

        # Create/update Claude provider config
        if settings.ANTHROPIC_API_KEY:
            claude_config, created = AIProviderConfig.objects.update_or_create(
                provider=AIProviderConfig.PROVIDER_CLAUDE,
                defaults={
                    'api_key': settings.ANTHROPIC_API_KEY,
                    'model_name': settings.ANTHROPIC_MODEL,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created Claude config with model {settings.ANTHROPIC_MODEL}'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Updated Claude config with model {settings.ANTHROPIC_MODEL}'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                '⚠ ANTHROPIC_API_KEY not found in environment, skipping Claude config'
            ))

        # Create/update global settings
        global_settings = AIGlobalSettings.get()
        global_settings.default_provider = settings.AI_DEFAULT_PROVIDER
        global_settings.fallback_provider = settings.AI_FALLBACK_PROVIDER
        global_settings.save()
        self.stdout.write(self.style.SUCCESS(
            f'✓ Updated global settings: default={settings.AI_DEFAULT_PROVIDER}, '
            f'fallback={settings.AI_FALLBACK_PROVIDER}'
        ))

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ AI configuration complete: '
            f'{created_count} created, {updated_count} updated'
        ))

