"""
Central mail dispatcher for Friday Mail Engine.
Handles mail hook resolution and dispatching mail tasks to Celery.
"""
from apps.mail.models import MailHook


def dispatch(event: str, context: dict, task=None, recipients_override: list[str] | None = None):
    """
    Central entry point for all mail notifications.

    Args:
        event: MailHook.EVENT_* constant
        context: Template context dictionary
        task: Task object (optional, for recipient resolution)
        recipients_override: Direct email addresses (overrides hook recipients)

    Checks:
    1. Hook active?
    2. Recipients have mail notifications enabled?
    3. Renders template
    4. Sends via MailService (Celery Task)
    """
    try:
        hook = MailHook.objects.get(event=event, is_active=True)
    except MailHook.DoesNotExist:
        return  # Hook inactive or doesn't exist — no error

    # Resolve recipients
    if recipients_override:
        recipients = recipients_override
    else:
        recipients = _resolve_recipients(hook, task)

    if not recipients:
        return

    # Render subject
    subject = hook.subject_template.format(**context)

    # Dispatch Celery task for each recipient
    from apps.mail.tasks import send_hook_mail
    for email in recipients:
        send_hook_mail.delay(
            template_name=hook.template_name,
            to=email,
            subject=subject,
            context=context,
        )


def _resolve_recipients(hook: MailHook, task) -> list[str]:
    """Resolve recipient types to email addresses."""
    emails = set()

    for recipient_type in hook.recipients:
        if not task:
            continue

        if recipient_type == 'assignee':
            if task.assigned_to_user and _wants_mail(task.assigned_to_user):
                emails.add(task.assigned_to_user.email)
            elif task.assigned_to_team:
                for m in task.assigned_to_team.memberships.all():
                    if _wants_mail(m.user):
                        emails.add(m.user.email)

        elif recipient_type == 'creator':
            if task.created_by and _wants_mail(task.created_by):
                emails.add(task.created_by.email)

        elif recipient_type == 'watchers':
            for u in task.watching_users.all():
                if _wants_mail(u):
                    emails.add(u.email)
            for team in task.watching_teams.all():
                for m in team.memberships.all():
                    if _wants_mail(m.user):
                        emails.add(m.user.email)

        elif recipient_type == 'project_manager':
            from apps.projects.models import ProjectUserMembership
            for m in ProjectUserMembership.objects.filter(project=task.project, role='manager'):
                if _wants_mail(m.user):
                    emails.add(m.user.email)

        elif recipient_type == 'portal_user':
            if task.created_by and task.created_by.is_portal_user:
                emails.add(task.created_by.email)

    return list(emails)


def _wants_mail(user) -> bool:
    """Check if user has email notifications enabled."""
    return bool(user.email and user.notify_email)
