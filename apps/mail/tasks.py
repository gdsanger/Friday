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
