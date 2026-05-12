"""
All AI prompt templates in one place.
Prompts are written in German for best model performance.
"""


def build_prompt(action: str, **kwargs) -> str:
    """Build a prompt for the specified AI action."""
    builders = {
        'summarize_task':      _summarize_task,
        'suggest_subtasks':    _suggest_subtasks,
        'task_description':    _task_description,
        'project_report':      _project_report,
        'mail_reply':          _mail_reply,
    }
    builder = builders.get(action)
    if not builder:
        raise ValueError(f'Unknown AI action: {action}')
    return builder(**kwargs)


def _summarize_task(task) -> str:
    comments = '\n'.join(
        f'- {c.author.full_name}: {c.body[:200]}'
        for c in task.comments.order_by('-created_at')[:5]
    )
    return f"""Fasse die folgende Projektaufgabe in 2-3 prägnanten Sätzen zusammen.
Fokus auf: Was muss erledigt werden, aktueller Status, und etwaige Blocker aus den Kommentaren.
Schließe mit einem Prioritätsvorschlag ab (Keine/Niedrig/Mittel/Hoch/Kritisch) auf einer neuen Zeile mit dem Präfix "Priorität: ".

Aufgabe: {task.title}
Beschreibung: {task.description or 'Keine Beschreibung.'}
Status: {task.get_status_display()}
Fällig: {task.due_date or 'Nicht gesetzt'}
Aktuelle Kommentare:
{comments or 'Noch keine Kommentare.'}

Antworte ausschließlich auf Deutsch."""


def _suggest_subtasks(task) -> str:
    return f"""Teile die folgende Aufgabe in 3-6 konkrete, umsetzbare Teilaufgaben auf.
Gib ausschließlich eine nummerierte Liste zurück. Jede Teilaufgabe in einem Satz, beginnend mit einem Verb.
Keine Einleitung, kein abschließender Kommentar.

Aufgabe: {task.title}
Beschreibung: {task.description or 'Keine Beschreibung vorhanden.'}

Antworte ausschließlich auf Deutsch."""


def _task_description(title: str) -> str:
    return f"""Schreibe eine klare, prägnante Aufgabenbeschreibung (3-5 Sätze) für eine Projektmanagement-Aufgabe mit folgendem Titel:
"{title}"

Beschreibe: Was muss getan werden, warum ist es wichtig, und welche offensichtlichen Erfolgskriterien gibt es.
Schreibe in einem professionellen, sachlichen Ton. Keine Markdown-Überschriften verwenden.

Antworte ausschließlich auf Deutsch."""


def _project_report(project) -> str:
    tasks       = project.tasks.all()
    total       = tasks.count()
    done        = tasks.filter(status='done').count()
    in_progress = tasks.filter(status='in_progress').count()
    overdue     = [t for t in tasks if t.is_overdue]

    return f"""Schreibe einen kurzen Projektstatusbericht (max. 200 Wörter) für das folgende Projekt.
Verwende einen professionellen Ton, geeignet für ein Team-Update per E-Mail.

Projekt: {project.name}
Status: {project.get_status_display()}
Fälligkeitsdatum: {project.due_date or 'Nicht gesetzt'}
Fortschritt: {done}/{total} Aufgaben abgeschlossen, {in_progress} in Bearbeitung
Überfällige Aufgaben: {len(overdue)}
Beschreibung: {project.description or 'Keine Beschreibung.'}

Antworte ausschließlich auf Deutsch."""


def _mail_reply(body: str, context: str) -> str:
    return f"""Verfasse eine professionelle Antwort auf die folgende E-Mail im Kontext einer Projektaufgabe.
Halte die Antwort kurz (3-5 Sätze). Keine Platzhalter wie [Name] verwenden.

Aufgabenkontext: {context}

Ursprüngliche E-Mail:
{body[:1500]}

Antworte ausschließlich auf Deutsch."""
