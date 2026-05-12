"""
Mail views for Friday project.
"""
import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import WebhookSubscription
from .tasks import process_incoming_mail

logger = logging.getLogger(__name__)


@csrf_exempt
def graph_webhook(request):
    """
    Endpoint: POST /api/mail/webhook/
    Receives Graph API change notifications for new inbox messages.
    Validates clientState, then dispatches Celery task to process each message.
    """
    # Graph API validation handshake
    validation_token = request.GET.get('validationToken')
    if validation_token:
        return HttpResponse(validation_token, content_type='text/plain')

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning('Invalid JSON in webhook payload')
        return HttpResponse(status=400)

    for notification in payload.get('value', []):
        client_state = notification.get('clientState', '')
        subscription_id = notification.get('subscriptionId', '')
        resource_data = notification.get('resourceData', {})
        message_id = resource_data.get('id')

        if not message_id:
            logger.warning(f'No message ID in notification for subscription {subscription_id}')
            continue

        # Validate clientState matches stored subscription
        sub = WebhookSubscription.objects.filter(
            subscription_id=subscription_id,
            client_state=client_state,
        ).select_related('user').first()

        if sub:
            process_incoming_mail.delay(sub.user.pk, message_id)
            logger.info(f'Queued processing for message {message_id} from user {sub.user.username}')
        else:
            logger.warning(f'Invalid clientState or subscription not found: {subscription_id}')

    return HttpResponse(status=202)
