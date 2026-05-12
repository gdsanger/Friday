# Projektverwaltung EOE-Verbund – Technische Spezifikation v2

## 1. Überblick & Architektur

### Organisationsmodell

```
EOE  (Dachorganisation / Verein)
│
├── Teams                          ← organisatorische Einheit
│    ├── IUN  (Marketing, HR, Finance)
│    ├── ISARtec  (IT, RZ, Dev)
│    ├── Hochschule A
│    ├── Hochschule B
│    └── ...
│
├── Projekte                       ← gehören zur EOE, nicht zu einem Team
│    ├── Mitglieder: User + Teams (mix möglich)
│    └── Sichtbarkeit: nur Projektmitglieder
│
└── Tasks
     ├── zugewiesen an: User  (konkrete Person)
     │                  Team  (wer im Team picked es up)
     └── Watcher: User + Teams
```

**Leitprinzip:** Maximale Flexibilität – nichts ist erzwungen.
Ein ISARtec-Mitglied kann in einem IUN-Projekt mitarbeiten.
Ein Task kann einem Team zugewiesen werden bis klar ist, wer ihn übernimmt.
Datentrennung erfolgt über Projektmitgliedschaft, nicht über Teamzugehörigkeit.

### Tech-Stack

| Schicht | Technologie |
|---|---|
| Backend | Python 3.12, Django 5.x |
| Frontend | HTMX 2.x, Bootstrap 5.x |
| Datenbank | PostgreSQL 16 |
| Authentifizierung | Django-Users + MSAL (Azure AD / Entra ID) |
| Mail | Microsoft Graph API – ein- & ausgehend |
| KI | OpenAI + Anthropic Claude (global, plattformweit) |
| Task Queue | Celery + Redis |
| Deployment | Docker / docker-compose |

---

## 2. Datenmodell

### 2.1 Organisation (Singleton)

```python
class Organisation(models.Model):
    """
    EOE – genau eine Instanz. Keine Multi-Tenancy.
    Plattformweite Einstellungen leben hier.
    """
    name        = models.CharField(max_length=200, default='EOE')
    slug        = models.SlugField(unique=True, default='eoe')
    logo        = models.ImageField(upload_to='org/', blank=True)
    description = models.TextField(blank=True)
    website     = models.URLField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Organisation"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton
        super().save(*args, **kwargs)
```

### 2.2 Teams

```python
class Team(models.Model):
    """
    Organisatorische Einheit (IUN, ISARtec, HS-A, ...).
    Steuert KEINE Datensichtbarkeit – nur Struktur & Assignment.
    """
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color       = models.CharField(max_length=7, default='#6366f1')  # HEX
    icon        = models.CharField(max_length=50, blank=True)         # Bootstrap-Icon-Name
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TeamMembership(models.Model):
    ROLE_CHOICES = [
        ('lead',   'Team Lead'),
        ('member', 'Mitglied'),
        ('guest',  'Gast'),       # z.B. Hochschul-Mitarbeiter in ISARtec-Team
    ]
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='team_memberships')
    team      = models.ForeignKey(Team, on_delete=models.CASCADE,
                                   related_name='memberships')
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'team')
        verbose_name = "Teammitgliedschaft"
```

### 2.3 Custom User

```python
class User(AbstractUser):
    """Erweiterter Django-User."""
    avatar        = models.ImageField(upload_to='avatars/', blank=True)
    display_name  = models.CharField(max_length=100, blank=True)
    job_title     = models.CharField(max_length=100, blank=True)
    phone         = models.CharField(max_length=30, blank=True)

    # Azure SSO
    azure_oid     = models.CharField(max_length=100, blank=True, unique=True, null=True)
    azure_upn     = models.EmailField(blank=True)   # UserPrincipalName

    # Präferenzen
    notify_email  = models.BooleanField(default=True)
    notify_inapp  = models.BooleanField(default=True)
    theme         = models.CharField(max_length=10, default='light',
                                      choices=[('light','Hell'),('dark','Dunkel')])
    timezone      = models.CharField(max_length=50, default='Europe/Berlin')

    @property
    def teams(self):
        return Team.objects.filter(memberships__user=self)

    @property
    def full_name(self):
        return self.display_name or self.get_full_name() or self.username
```

### 2.4 Projekte

```python
class Project(models.Model):
    STATUS_CHOICES = [
        ('planning',  'Planung'),
        ('active',    'Aktiv'),
        ('on_hold',   'Pausiert'),
        ('done',      'Abgeschlossen'),
        ('archived',  'Archiviert'),
    ]
    VISIBILITY_CHOICES = [
        ('members',      'Nur Mitglieder'),       # Standard
        ('organisation', 'Gesamte Organisation'), # alle EOE-User sehen es (read-only)
    ]

    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    visibility  = models.CharField(max_length=20, choices=VISIBILITY_CHOICES,
                                    default='members')
    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, related_name='owned_projects')
    start_date  = models.DateField(null=True, blank=True)
    due_date    = models.DateField(null=True, blank=True)
    priority    = models.IntegerField(default=0)
    color       = models.CharField(max_length=7, default='#3b82f6')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # Mitglieder: User direkt ODER via Team
    user_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectUserMembership',
        related_name='projects',
        blank=True,
    )
    team_members = models.ManyToManyField(
        Team,
        through='ProjectTeamMembership',
        related_name='projects',
        blank=True,
    )

    def get_all_members(self):
        """Alle effektiven Mitglieder: direkte User + alle aus beteiligten Teams."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        direct = self.user_members.all()
        via_team = User.objects.filter(
            team_memberships__team__in=self.team_members.all()
        )
        return (direct | via_team).distinct()

    def is_member(self, user):
        return user in self.get_all_members()

class ProjectUserMembership(models.Model):
    ROLE_CHOICES = [
        ('manager',     'Projektmanager'),
        ('contributor', 'Mitarbeiter'),
        ('viewer',      'Beobachter'),
    ]
    project   = models.ForeignKey(Project, on_delete=models.CASCADE)
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contributor')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')

class ProjectTeamMembership(models.Model):
    ROLE_CHOICES = [
        ('contributor', 'Mitarbeiter'),
        ('viewer',      'Beobachter'),
    ]
    project   = models.ForeignKey(Project, on_delete=models.CASCADE)
    team      = models.ForeignKey(Team, on_delete=models.CASCADE)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contributor')
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'team')
```

### 2.5 Tasks

```python
class Task(models.Model):
    STATUS_CHOICES = [
        ('backlog',     'Backlog'),
        ('todo',        'To Do'),
        ('in_progress', 'In Bearbeitung'),
        ('review',      'Review'),
        ('done',        'Erledigt'),
    ]
    PRIORITY_CHOICES = [
        (0, 'Keine'),
        (1, 'Niedrig'),
        (2, 'Mittel'),
        (3, 'Hoch'),
        (4, 'Kritisch'),
    ]

    title       = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    project     = models.ForeignKey(Project, on_delete=models.CASCADE,
                                     related_name='tasks')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='backlog')
    priority    = models.IntegerField(choices=PRIORITY_CHOICES, default=0)

    # Ersteller
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, related_name='created_tasks')

    # Assignment: Person ODER Team (nicht beides erzwingen)
    assigned_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks'
    )
    assigned_to_team = models.ForeignKey(
        Team, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks'
    )

    # Watcher: User UND/ODER Teams
    watching_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='watched_tasks'
    )
    watching_teams = models.ManyToManyField(
        Team, blank=True, related_name='watched_tasks'
    )

    # Zeitplanung
    due_date    = models.DateField(null=True, blank=True)
    estimated_h = models.DecimalField(max_digits=6, decimal_places=2,
                                       null=True, blank=True)

    # Hierarchie & Reihenfolge
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='subtasks')
    position    = models.IntegerField(default=0)

    labels      = models.ManyToManyField('Label', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    @property
    def assignee_display(self):
        """Zeigt Person oder Team-Name, je nachdem was gesetzt ist."""
        if self.assigned_to_user:
            return self.assigned_to_user.full_name
        if self.assigned_to_team:
            return f"Team: {self.assigned_to_team.name}"
        return "Nicht zugewiesen"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date and self.due_date < timezone.now().date() \
               and self.status != 'done'

    def get_all_watchers(self):
        """Effektive Watcher: direkte User + alle aus watching_teams."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        via_team = User.objects.filter(
            team_memberships__team__in=self.watching_teams.all()
        )
        return (self.watching_users.all() | via_team).distinct()
```

### 2.6 Weitere Modelle

```python
class Label(models.Model):
    name  = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#64748b')
    # global – kein Team/Projekt-Bezug, frei verwendbar

class Comment(models.Model):
    task        = models.ForeignKey(Task, on_delete=models.CASCADE,
                                     related_name='comments')
    author      = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE)
    body        = models.TextField()
    ai_summary  = models.TextField(blank=True)   # KI-Zusammenfassung langer Threads
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

class Attachment(models.Model):
    task        = models.ForeignKey(Task, on_delete=models.CASCADE,
                                     related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True)
    file        = models.FileField(upload_to='attachments/%Y/%m/')
    filename    = models.CharField(max_length=255)
    size_bytes  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

class TimeEntry(models.Model):
    task        = models.ForeignKey(Task, on_delete=models.CASCADE,
                                     related_name='time_entries')
    user        = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE)
    started_at  = models.DateTimeField()
    ended_at    = models.DateTimeField(null=True, blank=True)
    duration_m  = models.IntegerField(default=0)   # Minuten
    note        = models.TextField(blank=True)

class Notification(models.Model):
    recipient   = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE,
                                     related_name='notifications')
    verb        = models.CharField(max_length=100)  # z.B. "hat Task zugewiesen"
    actor       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     related_name='triggered_notifications')
    target_ct   = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_id   = models.PositiveIntegerField()
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
```

---

## 3. App-Struktur

```
eoe_projects/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── celery.py
│
├── apps/
│   ├── core/             # Organisation-Singleton, abstrakte Mixins, Utils
│   ├── accounts/         # CustomUser, Azure SSO (MSAL), Profil
│   ├── teams/            # Team-CRUD, TeamMembership
│   ├── projects/         # Projekt-CRUD, Mitglieder (User + Team)
│   ├── tasks/            # Task-CRUD, Assignment, Subtasks, Labels
│   ├── kanban/           # Projektübergreifendes Kanban-Board
│   ├── dashboard/        # KPI-Widgets, Aktivitäts-Feed
│   ├── mail/             # Graph API Mail-Integration
│   ├── ai/               # GlobalAIService (OpenAI + Claude)
│   ├── notifications/    # In-App-Benachrichtigungen
│   └── admin_panel/      # Einstellungen, User-Verwaltung, KI-Monitoring
│
├── templates/
│   ├── base.html
│   ├── partials/         # HTMX-Fragmente
│   ├── dashboard/
│   ├── teams/
│   ├── projects/
│   ├── tasks/
│   ├── kanban/
│   └── admin_panel/
│
├── static/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 4. Berechtigungsmodell

### Ebenen

```
Plattform-Admin (Django Superuser)
  └── Vollzugriff, KI-Konfiguration, User-Verwaltung

Projekt-Manager (ProjectUserMembership.role = 'manager')
  └── Projekt bearbeiten, Mitglieder verwalten, Tasks erstellen/löschen

Contributor (role = 'contributor' – direkt oder via Team)
  └── Tasks erstellen, bearbeiten, kommentieren, Zeit erfassen

Viewer (role = 'viewer' – direkt oder via Team)
  └── Nur lesen, kommentieren

Kein Mitglied
  └── Sieht Projekt nur wenn visibility = 'organisation'
      (dann read-only, keine Kommentare)
```

### Mixin für Views

```python
class ProjectMemberMixin:
    """Stellt sicher, dass der User Projektmitglied ist."""
    min_role = 'viewer'

    def dispatch(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs['project_pk'])
        membership = project.get_effective_membership(request.user)
        if not membership or not membership.has_min_role(self.min_role):
            raise PermissionDenied
        request.project = project
        request.project_role = membership.role
        return super().dispatch(request, *args, **kwargs)
```

---

## 5. Kanban-Board (projektübergreifend)

### Filter-Optionen

```
┌─────────────────────────────────────────────────────────────────┐
│  Filter:  [Projekt ▾]  [Team ▾]  [Priorität ▾]  [Fälligkeit ▾] │
│  Ansicht: [● Alle]  [○ Von mir erstellt]  [○ Mir zugewiesen]    │
│           [○ Meinem Team zugewiesen]  [○ Ich beobachte]         │
└─────────────────────────────────────────────────────────────────┘

┌─ Backlog ──┐  ┌─ To Do ────┐  ┌─ In Arbeit ┐  ┌─ Review ───┐  ┌─ Erledigt ─┐
│ [ISARtec]  │  │ [IUN]      │  │ [Max M.]   │  │ [IUN]      │  │ [Anna K.]  │
│ Task A     │  │ Task C     │  │ Task E     │  │ Task G     │  │ Task H     │
│ Projekt X  │  │ Projekt Y  │  │ Projekt X  │  │ Projekt Z  │  │ Projekt Y  │
└────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘
```

### Task-Karten zeigen

- Projekt-Farbe (linker Rand)
- Priorität (Icon)
- Assignee: Avatar (Person) oder Team-Badge
- Fälligkeitsdatum (rot wenn überfällig)
- Kommentar-Anzahl / Anhänge

### HTMX Filter-Query

```python
# apps/kanban/views.py
class KanbanBoardView(LoginRequiredMixin, View):
    def get(self, request):
        tasks = Task.objects.filter(
            project__in=Project.objects.accessible_by(request.user)
        ).select_related('project', 'assigned_to_user', 'assigned_to_team')

        # Filter anwenden
        if request.GET.get('view') == 'mine_created':
            tasks = tasks.filter(created_by=request.user)

        elif request.GET.get('view') == 'mine_assigned':
            tasks = tasks.filter(assigned_to_user=request.user)

        elif request.GET.get('view') == 'team_assigned':
            my_teams = request.user.teams
            tasks = tasks.filter(assigned_to_team__in=my_teams)

        elif request.GET.get('view') == 'watching':
            my_teams = request.user.teams
            tasks = tasks.filter(
                models.Q(watching_users=request.user) |
                models.Q(watching_teams__in=my_teams)
            ).distinct()

        if project_id := request.GET.get('project'):
            tasks = tasks.filter(project_id=project_id)

        if team_id := request.GET.get('team'):
            tasks = tasks.filter(
                models.Q(assigned_to_team_id=team_id) |
                models.Q(assigned_to_user__team_memberships__team_id=team_id)
            ).distinct()

        columns = {status: [] for status, _ in Task.STATUS_CHOICES}
        for task in tasks:
            columns[task.status].append(task)

        if request.htmx:
            return render(request, 'kanban/partials/board.html',
                          {'columns': columns})
        return render(request, 'kanban/board.html',
                      {'columns': columns, 'projects': ..., 'teams': ...})
```

---

## 6. Dashboard

### KPI-Widgets

```
┌─────────────────────────────────────────────────────┐
│  Meine Tasks heute      │  Überfällig    │  Offen   │
│  ████  12               │  ⚠  3          │  ●  47   │
├─────────────────────────┴────────────────┴──────────┤
│  Meinen Teams zugewiesene offene Tasks              │
│  ISARtec ████████░░  14     IUN ████░░░░  8         │
├─────────────────────────────────────────────────────┤
│  Projekte nach Status   │  Fällige Tasks (7 Tage)  │
│  [Donut Chart]          │  [Liste mit Projekt-Farbe]│
├─────────────────────────┴───────────────────────────┤
│  Letzte Aktivitäten                                 │
│  Anna K. hat Task "API Doku" abgeschlossen  2m      │
│  ISARtec wurde Task "Server Setup" zugewiesen  5m   │
└─────────────────────────────────────────────────────┘
```

### HTMX-Widget-System

```html
<!-- Jedes Widget lädt unabhängig, auto-refresh alle 60s -->
<div hx-get="/dashboard/widgets/my-tasks/"
     hx-trigger="load, every 60s"
     hx-target="this"
     hx-swap="outerHTML">
  <div class="widget-skeleton"></div>
</div>
```

---

## 7. KI-Integration (Global – Plattformweit)

> API-Keys und Konfiguration nur für Plattform-Admins (Superuser).
> Alle Teams und Projekte nutzen denselben Service ohne eigene Konfiguration.

### 7.1 Modell

```python
class AIProviderConfig(models.Model):
    PROVIDER_CHOICES = [('openai', 'OpenAI'), ('claude', 'Anthropic Claude')]
    provider        = models.CharField(max_length=20, choices=PROVIDER_CHOICES, unique=True)
    api_key         = EncryptedCharField(max_length=200)
    model_name      = models.CharField(max_length=100)
    is_active       = models.BooleanField(default=True)
    rpm_limit       = models.IntegerField(default=60)
    tpm_limit       = models.IntegerField(default=100_000)

class AIGlobalSettings(models.Model):
    """Singleton."""
    default_provider       = models.CharField(max_length=20, default='openai')
    fallback_provider      = models.CharField(max_length=20, blank=True)
    monthly_token_budget   = models.BigIntegerField(default=10_000_000)
    per_user_daily_limit   = models.IntegerField(default=50_000)
    is_enabled             = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

class AIUsageLog(models.Model):
    """Jeder API-Call wird geloggt – nach User und Team auswertbar."""
    user              = models.ForeignKey(settings.AUTH_USER_MODEL,
                                           on_delete=models.SET_NULL, null=True)
    team              = models.ForeignKey(Team, on_delete=models.SET_NULL,
                                           null=True, blank=True)
    provider          = models.CharField(max_length=20)
    action            = models.CharField(max_length=50)
    prompt_tokens     = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens      = models.IntegerField(default=0)
    duration_ms       = models.IntegerField(default=0)
    success           = models.BooleanField(default=True)
    error_message     = models.TextField(blank=True)
    object_type       = models.CharField(max_length=50, blank=True)
    object_id         = models.CharField(max_length=50, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
```

### 7.2 KI-Aktionen

| Aktion | Kontext | Ergebnis |
|---|---|---|
| Task-Zusammenfassung | Task-Detail | Kurztext + Prioritätsvorschlag |
| Subtask-Vorschläge | Task-Detail | Bestätigbare Teilaufgaben-Liste |
| Beschreibung generieren | Task-Erstellen | Beschreibung aus Titel |
| Projekt-Statusbericht | Projekt-Übersicht | Markdown-Report |
| Mail-Antwort-Entwurf | Eingehende Mail | Entwurf in Graph Mail |

### 7.3 Fallback-Logik

```
Request → Default Provider (OpenAI)
              │
              ├── OK → Antwort
              └── RateLimitError / Timeout
                    │
                    └── Fallback Provider (Claude)
                              │
                              ├── OK → Antwort + Log "fallback used"
                              └── Fehler → Fehlermeldung an User
```

---

## 8. Mail-Integration (Microsoft Graph API)

```python
# Eingehend: Webhook-Subscription
# Betreff-Erkennung: #TASK-123 → Kommentar anlegen
# Betreff-Erkennung: #PROJ-45  → Projektnotiz anlegen

# Ausgehend: Benachrichtigungen, Statusberichte, Direktmails aus Task-Detail
# Mail-Thread wird an Task verknüpft und ist dort sichtbar
```

---

## 9. Azure SSO (MSAL)

```python
MSAL_CONFIG = {
    'CLIENT_ID':     env('AZURE_CLIENT_ID'),
    'CLIENT_SECRET': env('AZURE_CLIENT_SECRET'),
    'TENANT_ID':     env('AZURE_TENANT_ID'),
    'AUTHORITY':     'https://login.microsoftonline.com/{tenant_id}',
    'SCOPES':        ['User.Read', 'Mail.ReadWrite', 'Mail.Send'],
    'REDIRECT_URI':  env('AZURE_REDIRECT_URI'),
}

# Login-Flow:
# /accounts/login/  →  Standard oder "Mit Microsoft anmelden"
#   → MSAL Auth Code Flow
#   → Callback: azure_oid auf User mappen / anlegen
#   → Weiter zu /dashboard/
```

---

## 10. Admin-Bereich (`/admin-panel/`)

> Eigener UI-Bereich – nicht Django-Admin

### Menü

```
Admin-Panel
├── Übersicht          Dashboard mit Systemstatus
├── Benutzer           Einladen, deaktivieren, Teams zuweisen
├── Teams              Teams anlegen, Mitglieder verwalten
├── Projekte           Alle Projekte, Archivierung
├── KI-Monitoring      Token-Verbrauch, Provider-Status, Budgets
│    ├── Verbrauch heute / Monat / gesamt
│    ├── Top-User / Top-Teams
│    ├── Provider aktivieren/deaktivieren
│    └── Fehler-Log
├── Mail-Einstellungen Graph API verbinden, Webhook-Status
├── Azure SSO          App-Registrierung, Callback-URL
└── Audit-Log          Alle sicherheitsrelevanten Aktionen
```

---

## 11. URL-Struktur

| URL | Beschreibung |
|---|---|
| `/` | Redirect → Dashboard |
| `/dashboard/` | KPI-Dashboard |
| `/dashboard/widgets/{name}/` | HTMX-Widget-Fragment |
| `/kanban/` | Projektübergreifendes Kanban |
| `/tasks/{id}/move/` | Task-Status via Drag & Drop |
| `/tasks/{id}/detail/` | Task-Slide-Over (HTMX) |
| `/tasks/{id}/assign/` | Assignment User/Team |
| `/tasks/{id}/watch/` | Watch/Unwatch |
| `/tasks/{id}/ai/{action}/` | KI-Aktion auf Task |
| `/projects/` | Projektliste |
| `/projects/{id}/` | Projektdetail |
| `/projects/{id}/members/` | Mitglieder verwalten |
| `/teams/` | Teamübersicht |
| `/teams/{id}/` | Team-Detail & Mitglieder |
| `/accounts/login/` | Login |
| `/accounts/azure/login/` | Azure SSO Start |
| `/accounts/azure/callback/` | Azure SSO Callback |
| `/admin-panel/` | Admin-Bereich |
| `/api/mail/webhook/` | Graph API Mail-Webhook |

---

## 12. Implementierungs-Phasen

### Phase 1 – Fundament (Woche 1–2)
- [ ] Django-Setup, Docker, PostgreSQL
- [ ] Organisation-Singleton, Team-Modelle, CustomUser
- [ ] Base-Templates (Bootstrap 5, HTMX)
- [ ] Standard-Login + Azure SSO (MSAL)
- [ ] Team-Verwaltung (CRUD, Mitglieder)

### Phase 2 – Projekte & Tasks (Woche 3–5)
- [ ] Projekt-CRUD (User + Team als Mitglieder)
- [ ] Task-CRUD (Assignment User/Team, Watcher)
- [ ] Kommentare, Anhänge, Labels
- [ ] Berechtigungssystem (ProjectMemberMixin)
- [ ] Subtasks

### Phase 3 – Kanban & Dashboard (Woche 6–7)
- [ ] Projektübergreifendes Kanban mit allen Filtern
- [ ] Drag & Drop (Sortable.js + HTMX)
- [ ] Dashboard KPI-Widgets
- [ ] In-App-Benachrichtigungen

### Phase 4 – Mail & KI (Woche 8–10)
- [ ] Graph API Mail (ein- & ausgehend)
- [ ] Mail-Thread an Task verknüpfen
- [ ] GlobalAIService (OpenAI + Claude + Fallback)
- [ ] KI-Aktionen in Task-UI
- [ ] Zeiterfassung

### Phase 5 – Admin & Finalisierung (Woche 11–12)
- [ ] Admin-Panel (alle Bereiche)
- [ ] KI-Monitoring Dashboard
- [ ] Audit-Log
- [ ] Performance-Optimierung (select_related, prefetch)
- [ ] Tests & Deployment

---

## 13. Docker & Konfiguration

### docker-compose.yml

```yaml
version: '3.9'
services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes: [.:/app]
    ports: ["8000:8000"]
    depends_on: [db, redis]
    env_file: .env

  db:
    image: postgres:16
    environment:
      POSTGRES_DB:       eoe_projects
      POSTGRES_USER:     django
      POSTGRES_PASSWORD: secret
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  celery:
    build: .
    command: celery -A config worker -l info
    depends_on: [db, redis]
    env_file: .env

  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on: [db, redis]
    env_file: .env

volumes:
  postgres_data:
```

### .env

```bash
# Django
SECRET_KEY=...
DEBUG=True
DATABASE_URL=postgresql://django:secret@db:5432/eoe_projects
REDIS_URL=redis://redis:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1

# Azure / MSAL
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
AZURE_REDIRECT_URI=http://localhost:8000/accounts/azure/callback/

# KI (global – nur Plattform-Admin)
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
AI_DEFAULT_PROVIDER=openai
AI_FALLBACK_PROVIDER=claude

# Verschlüsselung
FIELD_ENCRYPTION_KEY=...
```

### requirements.txt

```
Django>=5.1
psycopg[binary]>=3.2
django-environ
django-htmx
msal>=1.31
celery[redis]
django-celery-beat
httpx
openai>=1.50
anthropic>=0.40
django-encrypted-model-fields
Pillow
whitenoise
gunicorn
```
