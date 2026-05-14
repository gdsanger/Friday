"""
Celery tasks for mail processing.
"""
import re
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def process_incoming_mail(user_id: int, message_id: str):
    """
    Fetch full message from Graph API.
    Parse subject for task/project references (#TASK-123, #PROJ-45).
    Create Comment or Notification accordingly.
    """
    from django.contrib.auth import get_user_model
    from apps.tasks.models import Task, Comment
    from .service import MailService
    from .models import MailThread

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'User {user_id} not found for message {message_id}')
        return

    try:
        service = MailService(user=user)
        message = service.fetch_message(message_id)
    except Exception as e:
        logger.error(f'Failed to fetch message {message_id} for user {user_id}: {e}')
        return

    subject = message.get('subject', '')
    body = message.get('body', {}).get('content', '')
    sender_info = message.get('sender', {}).get('emailAddress', {})

    # Parse references
    task_ref = re.search(r'#TASK-(\d+)', subject + ' ' + body)

    if task_ref:
        try:
            task = Task.objects.get(pk=task_ref.group(1))
            Comment.objects.create(
                task=task,
                author=user,
                body=f'[Via Email] {body[:2000]}',
            )
            MailThread.objects.get_or_create(
                graph_message_id=message_id,
                defaults={
                    'task': task,
                    'direction': MailThread.DIRECTION_IN,
                    'subject': subject,
                    'sender_email': sender_info.get('address', ''),
                    'sender_name': sender_info.get('name', ''),
                    'body_preview': body[:500],
                    'received_at': message.get('receivedDateTime'),
                    'graph_conversation_id': message.get('conversationId', ''),
                }
            )
            logger.info(f'Created comment on Task {task.pk} from email {message_id}')
        except Task.DoesNotExist:
            logger.warning(f'Task {task_ref.group(1)} referenced in email {message_id} not found')
        except Exception as e:
            logger.error(f'Failed to process task reference in email {message_id}: {e}')


@shared_task
def renew_webhook_subscriptions():
    """
    Celery Beat task — runs daily.
    Renews all webhook subscriptions expiring within 24 hours.
    """
    from django.contrib.auth import get_user_model
    from .models import WebhookSubscription
    from .service import MailService

    User = get_user_model()

    expiring = WebhookSubscription.objects.filter(
        expiration__lte=timezone.now() + timedelta(hours=24)
    ).select_related('user')

    renewed_count = 0
    failed_count = 0

    for sub in expiring:
        try:
            service = MailService(user=sub.user)
            service.create_webhook_subscription()
            sub.delete()  # old subscription replaced
            renewed_count += 1
            logger.info(f'Renewed webhook subscription for user {sub.user.username}')
        except Exception as e:
            # Log error, don't crash beat
            logger.error(f'Webhook renewal failed for user {sub.user_id}: {e}')
            failed_count += 1

    logger.info(f'Webhook renewal complete: {renewed_count} renewed, {failed_count} failed')


# ── NEW MAIL ENGINE TASKS ─────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def send_hook_mail(self, template_name: str, to: str, subject: str, context: dict):
    """
    Send a single hook mail. Retry on error (3x).
    """
    try:
        from apps.mail.service_new import MailService
        MailService.send_template(
            to=[to],
            template_name=template_name,
            context=context,
            subject=subject,
        )
        logger.info(f'Sent mail "{subject}" to {to}')
    except Exception as exc:
        logger.error(f'Failed to send mail to {to}: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_daily_digest():
    """
    Täglich 07:00 Uhr.
    Sendet jedem aktiven User (notify_email=True) einen personalisierten
    Digest seiner Tasks in 3 Kategorien.
    Kein Digest wenn alle Kategorien leer sind.
    """
    from django.contrib.auth import get_user_model
    from apps.tasks.models import Task
    from apps.mail.dispatcher import dispatch
    from apps.mail.models import MailHook
    from django.conf import settings
    from django.db import models

    # Hook aktiv?
    try:
        hook = MailHook.objects.get(event=MailHook.EVENT_DAILY_DIGEST, is_active=True)
    except MailHook.DoesNotExist:
        logger.info('Daily digest hook is disabled')
        return  # Hook deaktiviert

    User = get_user_model()
    today = timezone.now().date()
    in_7 = today + timedelta(days=7)

    for user in User.objects.filter(
        is_active=True,
        notify_email=True,
        is_portal_user=False,
    ).prefetch_related('team_memberships__team'):

        my_teams = list(user.teams)

        # ── Kategorie 1: Überfällig ───────────────────────────────
        # XOR Logic: Direkt zugewiesen ODER Team ohne User-Assignee
        overdue = Task.objects.filter(
            models.Q(assigned_to_user=user) |
            models.Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True),
            due_date__lt=today,
        ).exclude(status='done').select_related(
            'project', 'assigned_to_team', 'assigned_to_user'
        ).order_by('due_date')

        # ── Kategorie 2: Nächste 7 Tage ──────────────────────────
        # XOR Logic: Direkt zugewiesen ODER Team ohne User-Assignee
        upcoming = Task.objects.filter(
            models.Q(assigned_to_user=user) |
            models.Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True),
            due_date__range=(today, in_7),
        ).exclude(status='done').select_related(
            'project', 'assigned_to_team', 'assigned_to_user'
        ).order_by('due_date')

        # ── Kategorie 3: In Bearbeitung ───────────────────────────
        # XOR Logic: Direkt zugewiesen ODER Team ohne User-Assignee
        in_progress = Task.objects.filter(
            models.Q(assigned_to_user=user) |
            models.Q(assigned_to_team__in=my_teams, assigned_to_user__isnull=True),
            status='in_progress',
        ).select_related(
            'project', 'assigned_to_team', 'assigned_to_user'
        ).order_by('-updated_at')[:10]

        # Kein Digest wenn alles leer
        if not overdue.exists() and not upcoming.exists() and not in_progress.exists():
            continue

        # Task-Daten serialisieren (Celery überträgt keine ORM-Objekte)
        def serialize_tasks(qs):
            return [
                {
                    'title': t.title,
                    'project_name': t.project.name,
                    'project_color': t.project.color,
                    'due_date': t.due_date.strftime('%d.%m.%Y') if t.due_date else '',
                    'priority': t.get_priority_display(),
                    'priority_val': t.priority,
                    'status': t.get_status_display(),
                    'assignee': t.assigned_to_team.name if t.assigned_to_team
                                else (t.assigned_to_user.full_name if t.assigned_to_user else ''),
                    'url': f'{settings.SITE_URL}/tasks/{t.pk}/',
                    'is_team': t.assigned_to_team_id is not None,
                }
                for t in qs
            ]

        dispatch(
            event=MailHook.EVENT_DAILY_DIGEST,
            context={
                'recipient_name': user.full_name,
                'today_str': today.strftime('%A, %d. %B %Y'),
                'date': today.strftime('%d.%m.%Y'),
                'overdue_tasks': serialize_tasks(overdue),
                'upcoming_tasks': serialize_tasks(upcoming),
                'in_progress_tasks': serialize_tasks(in_progress),
                'overdue_count': overdue.count(),
                'upcoming_count': upcoming.count(),
                'in_progress_count': in_progress.count(),
                'kanban_url': f'{settings.SITE_URL}/kanban/?view=mine_assigned',
                'profile_url': f'{settings.SITE_URL}/accounts/profile/',
            },
            recipients_override=[user.email],
        )
        logger.info(f'Sent daily digest to {user.email}')


@shared_task
def send_overdue_notifications():
    """
    Celery Beat — daily at 08:00.
    Notifies assignees about overdue tasks (once per task/day).
    """
    from apps.tasks.models import Task
    from django.conf import settings
    from .dispatcher import dispatch

    today = timezone.now().date()
    overdue = Task.objects.filter(
        due_date__lt=today,
        assigned_to_user__isnull=False,
    ).exclude(status='done').select_related(
        'assigned_to_user', 'project'
    )

    for task in overdue:
        dispatch(
            event='task_overdue',
            context={
                'recipient_name': task.assigned_to_user.full_name,
                'task_title': task.title,
                'task_url': f'{settings.SITE_URL}/tasks/{task.pk}/',
                'project_name': task.project.name,
                'due_date': task.due_date.strftime('%d.%m.%Y'),
            },
            task=task,
        )
        logger.info(f'Sent overdue notification for task {task.pk}')


@shared_task
def send_invitation_mail(user_id: int):
    """
    Send invitation mail to newly provisioned user.
    Uses the new mail engine with user_invited event.
    """
    from django.contrib.auth import get_user_model
    from django.conf import settings
    from .dispatcher import dispatch
    from .models import MailHook

    User = get_user_model()

    try:
        user = User.objects.select_related('portal_client').get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'User {user_id} not found for invitation email')
        return

    dispatch(
        event=MailHook.EVENT_USER_INVITED,
        context={
            'recipient_name': user.display_name or user.username,
            'login_url': f'{settings.SITE_URL}/accounts/azure/login/',
            'app_url': settings.SITE_URL,
            'user_type': 'Portal' if user.is_portal_user else 'Friday',
            'portal_client': user.portal_client.name if user.portal_client else '',
        },
        recipients_override=[user.email],
    )

