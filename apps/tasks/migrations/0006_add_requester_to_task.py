# Generated migration for adding requester field to Task model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tasks', '0005_add_story_points_to_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='requester',
            field=models.ForeignKey(
                blank=True,
                help_text='Person die diese Arbeit angefordert hat. Kann von "Erstellt von" abweichen.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='requested_tasks',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
