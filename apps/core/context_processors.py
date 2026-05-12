"""
Context processors for Friday project.
Provides global template variables.
"""


def friday_context(request):
    """
    Add Friday-specific context variables to all templates.
    """
    context = {
        'app_version': '1.0.0',
        'user_teams': [],
        'unread_notification_count': 0,
    }

    # Add user teams and unread notifications if authenticated
    if request.user.is_authenticated:
        try:
            context['user_teams'] = list(request.user.teams.all()) if hasattr(request.user, 'teams') else []
        except Exception:
            # Teams model may not be available yet
            context['user_teams'] = []

        try:
            from apps.notifications.models import Notification
            context['unread_notification_count'] = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()
        except Exception:
            # Notification model may not be available yet
            context['unread_notification_count'] = 0

    return context
