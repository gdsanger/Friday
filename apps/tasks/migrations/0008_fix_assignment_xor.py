# Generated manually for ISSUE-49
from django.db import migrations


def fix_double_assignments(apps, schema_editor):
    """
    Tasks die sowohl assigned_to_user als auch assigned_to_team haben:
    → assigned_to_team leeren (User hat Vorrang)
    """
    Task = apps.get_model('tasks', 'Task')
    double_assigned = Task.objects.filter(
        assigned_to_user__isnull=False,
        assigned_to_team__isnull=False,
    )
    count = double_assigned.count()
    if count > 0:
        double_assigned.update(assigned_to_team=None)
        print(f'Fixed {count} tasks with double assignments (kept user, cleared team)')


def reverse_fix(apps, schema_editor):
    """No reverse operation - we can't restore the data we don't know."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_add_task_template'),
    ]

    operations = [
        migrations.RunPython(fix_double_assignments, reverse_fix),
    ]
