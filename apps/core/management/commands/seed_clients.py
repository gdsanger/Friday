"""
Management command to seed initial clients for Friday project.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.core.models import Client


INITIAL_CLIENTS = [
    {'name': 'HAM',     'short_name': 'HAM',  'color': '#2d6a4f'},
    {'name': 'DHGS',    'short_name': 'DHGS', 'color': '#2980b9'},
    {'name': 'HSSH',    'short_name': 'HSSH', 'color': '#8e44ad'},
    {'name': 'Seeburg', 'short_name': 'SBG',  'color': '#e07c24'},
    {'name': 'Intern',  'short_name': 'INT',  'color': '#6b7280'},
]


class Command(BaseCommand):
    help = 'Seed initial client data for EOE'

    def handle(self, *args, **options):
        self.stdout.write('Seeding clients...')
        created = 0
        skipped = 0

        for client_data in INITIAL_CLIENTS:
            name = client_data['name']
            slug = slugify(name)

            if Client.objects.filter(slug=slug).exists():
                self.stdout.write(
                    self.style.WARNING(f'  Client "{name}" already exists, skipping.')
                )
                skipped += 1
                continue

            Client.objects.create(
                name=name,
                slug=slug,
                short_name=client_data['short_name'],
                color=client_data['color'],
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Created client: {name} ({client_data["short_name"]})')
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeeding complete! Created {created}, skipped {skipped}.'
            )
        )
