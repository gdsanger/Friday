"""
Management command to seed standard Mail Hooks.
Safe to run multiple times (uses get_or_create).

Usage: python manage.py seed_mail_hooks
"""
from django.core.management.base import BaseCommand
from apps.mail.models import MailHook


HOOKS = [
    {
        'event': 'task_assigned',
        'template_name': 'task_assigned',
        'subject_template': 'New task assigned: {task_title}',
        'recipients': ['assignee'],
        'is_active': True,
        'description': 'Sent when a task is assigned to a person or team.',
    },
    {
        'event': 'task_done',
        'template_name': 'task_done',
        'subject_template': 'Task completed: {task_title}',
        'recipients': ['creator', 'watchers'],
        'is_active': True,
        'description': 'Sent when a task is set to "Done".',
    },
    {
        'event': 'task_comment',
        'template_name': 'task_comment',
        'subject_template': 'New comment: {task_title}',
        'recipients': ['assignee', 'creator', 'watchers'],
        'is_active': False,  # Default: off
        'description': 'Sent when a comment is added.',
    },
    {
        'event': 'task_overdue',
        'template_name': 'task_overdue',
        'subject_template': 'Overdue task: {task_title}',
        'recipients': ['assignee'],
        'is_active': True,
        'description': 'Sent daily for overdue tasks (via Celery Beat).',
    },
    {
        'event': 'portal_ticket_created',
        'template_name': 'portal_ticket_created',
        'subject_template': 'Your request has been received: {task_title}',
        'recipients': ['portal_user'],
        'is_active': True,
        'description': 'Confirmation email for portal users.',
    },
    {
        'event': 'portal_ticket_done',
        'template_name': 'portal_ticket_done',
        'subject_template': 'Your request has been completed: {task_title}',
        'recipients': ['portal_user'],
        'is_active': True,
        'description': 'Completion notification for portal users.',
    },
    {
        'event': 'daily_digest',
        'template_name': 'daily_digest',
        'subject_template': 'Friday Summary – {date}',
        'recipients': ['assignee'],
        'is_active': True,
        'description': 'Daily summary of open and overdue tasks (07:00).',
    },
    {
        'event': 'user_invited',
        'template_name': 'user_invited',
        'subject_template': 'You have been invited to Friday',
        'recipients': [],  # Recipients passed directly
        'is_active': True,
        'description': 'Invitation email for new users.',
    },
]


class Command(BaseCommand):
    help = 'Seed standard Mail Hooks (idempotent)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Seeding Mail Hooks...'))

        created_count = 0
        updated_count = 0

        for hook_data in HOOKS:
            hook, created = MailHook.objects.get_or_create(
                event=hook_data['event'],
                defaults={
                    'template_name': hook_data['template_name'],
                    'subject_template': hook_data['subject_template'],
                    'recipients': hook_data['recipients'],
                    'is_active': hook_data['is_active'],
                    'description': hook_data['description'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {hook.get_event_display()}')
                )
            else:
                # Update existing hook with new values
                hook.template_name = hook_data['template_name']
                hook.subject_template = hook_data['subject_template']
                hook.recipients = hook_data['recipients']
                hook.description = hook_data['description']
                # Do NOT overwrite is_active — preserve user's choice
                hook.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  → Updated: {hook.get_event_display()}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Created {created_count}, updated {updated_count} hooks.'
            )
        )
