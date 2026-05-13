# Generated manually for ISSUE-34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailHook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(choices=[('task_created', 'Task created'), ('task_assigned', 'Task assigned'), ('task_done', 'Task completed'), ('task_comment', 'Comment added'), ('task_overdue', 'Task overdue'), ('portal_ticket_created', 'Portal: Ticket received'), ('portal_ticket_done', 'Portal: Ticket completed'), ('daily_digest', 'Daily summary'), ('user_invited', 'User invited')], max_length=50, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('recipients', models.JSONField(default=list, help_text='List of recipient types, e.g. ["assignee", "watchers"]')),
                ('template_name', models.CharField(help_text='Template filename without .html, e.g. task_assigned', max_length=100)),
                ('subject_template', models.CharField(help_text='Subject template, e.g. "New task: {task_title}"', max_length=200)),
                ('description', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Mail Hook',
                'verbose_name_plural': 'Mail Hooks',
                'ordering': ['event'],
            },
        ),
    ]
