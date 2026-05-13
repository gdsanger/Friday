# Generated migration for adding TaskTemplate model and template field to Task

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
        ('teams', '0001_initial'),
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tasks', '0006_add_requester_to_task'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True, help_text='Interne Beschreibung der Vorlage.')),
                ('default_priority', models.IntegerField(choices=[], default=0)),
                ('extra_fields_yaml', models.TextField(blank=True, help_text='''YAML-Definition der Zusatzfelder.
Beispiel:
- name: zielgruppe
  label: Zielgruppe
  type: text
  required: true

- name: ton
  label: Ton der Kommunikation
  type: select
  required: true
  options:
    - Formell
    - Informell
    - Neutral
''')),
                ('is_active', models.BooleanField(default=True)),
                ('is_portal_visible', models.BooleanField(default=False, help_text='Im Customer Portal verfügbar.')),
                ('client', models.ForeignKey(
                    blank=True,
                    help_text='Nur für diesen Mandanten sichtbar. Leer = alle Mandanten.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='core.client'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL
                )),
                ('default_assigned_to_team', models.ForeignKey(
                    blank=True,
                    help_text='Vorausgewähltes Team.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='teams.team'
                )),
                ('default_project', models.ForeignKey(
                    blank=True,
                    help_text='Vorausgewähltes Projekt.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='projects.project'
                )),
            ],
            options={
                'verbose_name': 'Task Template',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='task',
            name='template',
            field=models.ForeignKey(
                blank=True,
                help_text='Template aus dem dieser Task erstellt wurde.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_tasks',
                to='tasks.tasktemplate'
            ),
        ),
    ]
