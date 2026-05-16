"""
Task models for Friday project.
"""
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class TaskTemplate(TimeStampedModel):
    """
    Wiederverwendbare Task-Vorlage.
    extra_fields_yaml definiert Zusatzfelder als YAML.
    Nur Staff kann Templates anlegen/bearbeiten.
    """
    name                = models.CharField(max_length=200)
    slug                = models.SlugField(unique=True)
    description         = models.TextField(
                            blank=True,
                            help_text='Interne Beschreibung der Vorlage.'
                          )
    # Standard-Felder Defaults
    default_project     = models.ForeignKey(
                            'projects.Project',
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            help_text='Vorausgewähltes Projekt.'
                          )
    default_priority    = models.IntegerField(
                            choices=[],  # Will be set dynamically
                            default=0
                          )
    default_assigned_to_team = models.ForeignKey(
                            'teams.Team',
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            help_text='Vorausgewähltes Team.'
                          )

    # Zusatzfelder als YAML
    extra_fields_yaml   = models.TextField(
                            blank=True,
                            help_text='''YAML-Definition der Zusatzfelder.
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
'''
                          )

    # Sichtbarkeit
    is_active           = models.BooleanField(default=True)
    is_portal_visible   = models.BooleanField(
                            default=False,
                            help_text='Im Customer Portal verfügbar.'
                          )
    client              = models.ForeignKey(
                            'core.Client',
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            help_text='Nur für diesen Mandanten sichtbar. '
                                      'Leer = alle Mandanten.'
                          )
    created_by          = models.ForeignKey(
                            settings.AUTH_USER_MODEL,
                            on_delete=models.SET_NULL,
                            null=True
                          )

    class Meta:
        ordering = ['name']
        verbose_name = 'Task Template'

    def __str__(self):
        return self.name

    def get_extra_fields(self) -> list:
        """
        Parst extra_fields_yaml und gibt eine Liste von Feld-Definitionen zurück.
        Gibt [] zurück wenn kein YAML definiert oder YAML ungültig.
        """
        if not self.extra_fields_yaml:
            return []
        try:
            import yaml
            fields = yaml.safe_load(self.extra_fields_yaml)
            return fields if isinstance(fields, list) else []
        except yaml.YAMLError:
            return []

    def validate_yaml(self) -> tuple:
        """
        Validiert das YAML. Gibt (True, '') oder (False, Fehlermeldung) zurück.
        Wird im Admin und im Edit-View aufgerufen.
        """
        if not self.extra_fields_yaml:
            return True, ''
        try:
            import yaml
            fields = yaml.safe_load(self.extra_fields_yaml)
            if not isinstance(fields, list):
                return False, 'YAML muss eine Liste von Feldern sein.'

            valid_types = {'text', 'textarea', 'number', 'select',
                           'multiselect', 'date', 'checkbox'}

            for i, field in enumerate(fields):
                if not isinstance(field, dict):
                    return False, f'Feld {i+1}: muss ein Objekt sein.'
                if 'name' not in field:
                    return False, f'Feld {i+1}: "name" fehlt.'
                if 'label' not in field:
                    return False, f'Feld {i+1}: "label" fehlt.'
                if 'type' not in field:
                    return False, f'Feld {i+1}: "type" fehlt.'
                if field['type'] not in valid_types:
                    return False, f'Feld {i+1}: ungültiger type "{field["type"]}". ' \
                                  f'Erlaubt: {", ".join(valid_types)}'
                if field['type'] in ('select', 'multiselect'):
                    if 'options' not in field or not isinstance(field['options'], list):
                        return False, f'Feld {i+1} ({field["type"]}): "options" ' \
                                      f'fehlt oder ist keine Liste.'

            return True, ''
        except Exception as e:
            return False, f'YAML-Fehler: {str(e)}'


class Label(models.Model):
    """Label model for categorizing tasks."""
    name  = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#64748b')

    def __str__(self):
        return self.name


class Task(TimeStampedModel):
    """Task model for tracking work items."""
    STATUS_BACKLOG      = 'backlog'
    STATUS_TODO         = 'todo'
    STATUS_IN_PROGRESS  = 'in_progress'
    STATUS_WAITING      = 'waiting'
    STATUS_REVIEW       = 'review'
    STATUS_DONE         = 'done'
    STATUS_CHOICES = [
        (STATUS_BACKLOG,     'Backlog'),
        (STATUS_TODO,        'To Do'),
        (STATUS_IN_PROGRESS, 'In Bearbeitung'),
        (STATUS_WAITING,     'Waiting'),
        (STATUS_REVIEW,      'Review'),
        (STATUS_DONE,        'Erledigt'),
    ]
    PRIORITY_NONE     = 0
    PRIORITY_LOW      = 1
    PRIORITY_MEDIUM   = 2
    PRIORITY_HIGH     = 3
    PRIORITY_CRITICAL = 4
    PRIORITY_CHOICES = [
        (PRIORITY_NONE,     'None'),
        (PRIORITY_LOW,      'Low'),
        (PRIORITY_MEDIUM,   'Medium'),
        (PRIORITY_HIGH,     'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    title       = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    project     = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_BACKLOG
    )
    priority    = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NONE
    )
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    requester   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_tasks',
        help_text='Person die diese Arbeit angefordert hat. '
                  'Kann von "Erstellt von" abweichen.'
    )

    # Assignment: user OR team (both nullable — unassigned is valid)
    assigned_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    assigned_to_team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    # Watchers: users AND/OR teams
    watching_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='watched_tasks'
    )
    watching_teams = models.ManyToManyField(
        'teams.Team',
        blank=True,
        related_name='watched_tasks'
    )

    client      = models.ForeignKey(
        'core.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text='Client / Mandant — inherited from project if not set directly.'
    )
    due_date    = models.DateField(null=True, blank=True)
    deadline    = models.DateField(
        null=True,
        blank=True,
        help_text='Hard deadline for this task — shown as milestone in calendar.'
    )
    estimated_h = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    story_points = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Story Points (1 SP = 1 Stunde). Schätzung des Aufwands.'
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subtasks'
    )
    position    = models.IntegerField(default=0)
    labels      = models.ManyToManyField(Label, blank=True)
    template    = models.ForeignKey(
        'TaskTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_tasks',
        help_text='Template aus dem dieser Task erstellt wurde.'
    )

    class Meta:
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assigned_to_user']),
            models.Index(fields=['assigned_to_team']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """Validate that task is assigned to either user OR team, not both."""
        from django.core.exceptions import ValidationError
        if self.assigned_to_user_id and self.assigned_to_team_id:
            raise ValidationError(
                'Ein Task kann nicht gleichzeitig einem User '
                'und einem Team zugewiesen sein.'
            )

    def save(self, *args, **kwargs):
        """Call clean() before saving to enforce XOR constraint."""
        self.clean()
        super().save(*args, **kwargs)

    @property
    def assignee_display(self):
        """Return a string representation of the assignee."""
        if self.assigned_to_user:
            return self.assigned_to_user.full_name
        if self.assigned_to_team:
            return f'Team: {self.assigned_to_team.name}'
        return 'Unassigned'

    @property
    def effective_client(self):
        """Return the client for this task (direct or inherited from project)."""
        return self.client or (self.project.client if self.project else None)

    @property
    def effective_requester(self):
        """Return requester or created_by if requester is not set."""
        return self.requester or self.created_by

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        from django.utils import timezone
        return (
            self.due_date
            and self.due_date < timezone.now().date()
            and self.status != self.STATUS_DONE
        )

    def get_all_watchers(self):
        """Get all users watching this task (direct + via teams)."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        via_team = User.objects.filter(
            team_memberships__team__in=self.watching_teams.all()
        )
        return (self.watching_users.all() | via_team).distinct()

    @property
    def blocking_tasks(self):
        """Tasks that must be done before this task can start."""
        return Task.objects.filter(blocks_deps__task=self)

    @property
    def is_blocked(self):
        """True if any blocking task is not yet done."""
        return self.blocked_by_deps.exclude(
            blocked_by__status=Task.STATUS_DONE
        ).exists()

    @property
    def blocked_tasks(self):
        """Tasks that are waiting for this task to be done."""
        return Task.objects.filter(blocked_by_deps__blocked_by=self)

    @property
    def checklist_progress(self):
        """Gibt (erledigt, gesamt) zurück."""
        items = self.checklist_items.all()
        total = items.count()
        done  = items.filter(is_done=True).count()
        return done, total

    @property
    def checklist_pct(self):
        """Fortschritt in Prozent."""
        done, total = self.checklist_progress
        if total == 0:
            return 0
        return int(done / total * 100)


class Comment(TimeStampedModel):
    """Comment model for task discussions."""
    task       = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    body       = models.TextField()
    ai_summary = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.task.title}'


class Attachment(models.Model):
    """Attachment model for task files."""
    task        = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    file        = models.FileField(upload_to='attachments/%Y/%m/')
    filename    = models.CharField(max_length=255)
    size_bytes  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class TimeEntry(TimeStampedModel):
    """Time entry model for tracking work time on tasks."""
    task       = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='time_entries'
    )
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    started_at = models.DateTimeField()
    ended_at   = models.DateTimeField(null=True, blank=True)
    duration_m = models.IntegerField(default=0)  # minutes
    note       = models.TextField(blank=True)

    def __str__(self):
        return f'{self.user.username} - {self.task.title} ({self.duration_m}m)'


class TaskDependency(models.Model):
    """
    Represents a "blocked by" relationship between two tasks.
    task is blocked by blocked_by.
    """
    task       = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='blocked_by_deps'
    )
    blocked_by = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='blocks_deps'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'blocked_by')
        verbose_name = 'Task Dependency'
        verbose_name_plural = 'Task Dependencies'

    def __str__(self):
        return f'{self.task.title} blocked by {self.blocked_by.title}'


class ChecklistTemplate(TimeStampedModel):
    """
    Wiederverwendbare Checklisten-Vorlage.
    Nur Staff kann Vorlagen anlegen.
    """
    name       = models.CharField(max_length=200, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ChecklistTemplateItem(models.Model):
    """Ein Eintrag in einer Checklisten-Vorlage."""
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name='items'
    )
    title    = models.CharField(max_length=300)
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class TaskChecklistItem(TimeStampedModel):
    """
    Ein Checklisten-Item an einem konkreten Task.
    Entweder manuell erstellt oder aus einer Vorlage.
    """
    task      = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='checklist_items'
    )
    title     = models.CharField(max_length=300)
    is_done   = models.BooleanField(default=False)
    order     = models.PositiveIntegerField(default=0)
    done_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='checked_items'
    )
    done_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{"☑" if self.is_done else "☐"} {self.title}'


class TaskActivity(models.Model):
    """
    Audit-Log für alle relevanten Änderungen an einem Task.
    Unveränderlich — keine Updates, nur Inserts.
    """

    # Verfügbare Verben
    VERB_CREATED          = 'created'
    VERB_STATUS_CHANGED   = 'status_changed'
    VERB_ASSIGNED         = 'assigned'
    VERB_UNASSIGNED       = 'unassigned'
    VERB_PRIORITY_CHANGED = 'priority_changed'
    VERB_DEADLINE_CHANGED = 'deadline_changed'
    VERB_DUE_DATE_CHANGED = 'due_date_changed'
    VERB_CLOSED           = 'closed'
    VERB_COMMENTED        = 'commented'
    VERB_WATCHER_ADDED    = 'watcher_added'
    VERB_WATCHER_REMOVED  = 'watcher_removed'
    VERB_PROJECT_MOVED    = 'project_moved'
    VERB_TITLE_CHANGED    = 'title_changed'
    VERB_SP_CHANGED       = 'sp_changed'

    VERB_CHOICES = [
        (VERB_CREATED,          'erstellt'),
        (VERB_STATUS_CHANGED,   'Status geändert'),
        (VERB_ASSIGNED,         'zugewiesen'),
        (VERB_UNASSIGNED,       'Zuweisung entfernt'),
        (VERB_PRIORITY_CHANGED, 'Priorität geändert'),
        (VERB_DEADLINE_CHANGED, 'Deadline geändert'),
        (VERB_DUE_DATE_CHANGED, 'Fälligkeitsdatum geändert'),
        (VERB_CLOSED,           'abgeschlossen'),
        (VERB_COMMENTED,        'kommentiert'),
        (VERB_WATCHER_ADDED,    'Watcher hinzugefügt'),
        (VERB_WATCHER_REMOVED,  'Watcher entfernt'),
        (VERB_PROJECT_MOVED,    'Projekt gewechselt'),
        (VERB_TITLE_CHANGED,    'Titel geändert'),
        (VERB_SP_CHANGED,       'Story Points geändert'),
    ]

    task       = models.ForeignKey(
        'Task', on_delete=models.CASCADE,
        related_name='activities'
    )
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_activities'
    )
    verb       = models.CharField(max_length=50, choices=VERB_CHOICES)
    old_value  = models.CharField(max_length=500, blank=True)
    new_value  = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Activity'

    def __str__(self):
        return f'{self.user} {self.verb} on {self.task}'

    @property
    def display_text(self):
        """Menschenlesbarer Text für die Activity."""
        user = self.user.full_name if self.user else 'System'
        verb = self.get_verb_display()

        templates = {
            'created':          f'{user} hat den Task erstellt',
            'status_changed':   f'{user} hat Status von "{self.old_value}" auf "{self.new_value}" geändert',
            'assigned':         f'{user} hat Task "{self.new_value}" zugewiesen',
            'unassigned':       f'{user} hat Zuweisung entfernt',
            'priority_changed': f'{user} hat Priorität von "{self.old_value}" auf "{self.new_value}" geändert',
            'deadline_changed': f'{user} hat Deadline auf {self.new_value} gesetzt',
            'due_date_changed': f'{user} hat Fälligkeitsdatum auf {self.new_value} gesetzt',
            'closed':           f'{user} hat Task abgeschlossen ({self.new_value}h erfasst)',
            'commented':        f'{user} hat einen Kommentar hinzugefügt',
            'watcher_added':    f'{user} hat {self.new_value} als Watcher hinzugefügt',
            'watcher_removed':  f'{user} hat {self.new_value} als Watcher entfernt',
            'project_moved':    f'{user} hat Task nach "{self.new_value}" verschoben',
            'title_changed':    f'{user} hat Titel geändert',
            'sp_changed':       f'{user} hat Story Points auf {self.new_value} SP geändert',
        }
        return templates.get(self.verb, f'{user} hat {verb}')
