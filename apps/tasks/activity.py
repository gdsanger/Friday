"""
Helper functions for task activity logging.
"""


def log_activity(task, user, verb, old_value='', new_value=''):
    """
    Erstellt einen Activity-Eintrag für einen Task.
    Sicher aufzurufen — wirft keine Exceptions.

    Args:
        task: Task instance
        user: User instance who performed the action
        verb: One of TaskActivity.VERB_* constants
        old_value: Previous value (optional)
        new_value: New value (optional)
    """
    try:
        from .models import TaskActivity
        TaskActivity.objects.create(
            task      = task,
            user      = user,
            verb      = verb,
            old_value = str(old_value) if old_value else '',
            new_value = str(new_value) if new_value else '',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f'Failed to log activity for task {task.pk}: {e}'
        )
