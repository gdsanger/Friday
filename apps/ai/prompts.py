"""
All AI prompt templates in one place.
Prompts are written in English for best model performance.
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
    """Generate prompt for task summarization."""
    comments = '\n'.join(
        f'- {c.author.full_name}: {c.body[:200]}'
        for c in task.comments.order_by('-created_at')[:5]
    )
    return f"""Summarize the following project task in 2-3 concise sentences.
Focus on: what needs to be done, current status, and any blockers mentioned in comments.
End with a suggested priority (None/Low/Medium/High/Critical) on a new line prefixed with "Priority: ".

Task: {task.title}
Description: {task.description or 'No description.'}
Status: {task.get_status_display()}
Due: {task.due_date or 'Not set'}
Recent comments:
{comments or 'No comments yet.'}"""


def _suggest_subtasks(task) -> str:
    """Generate prompt for subtask suggestions."""
    return f"""Break down the following task into 3-6 concrete, actionable subtasks.
Return a numbered list only. Each subtask should be 1 sentence, starting with a verb.
Do not add any introduction or closing remarks.

Task: {task.title}
Description: {task.description or 'No description provided.'}"""


def _task_description(title: str) -> str:
    """Generate prompt for task description creation."""
    return f"""Write a clear, concise task description (3-5 sentences) for a project management task with this title:
"{title}"

Include: what needs to be done, why it matters, and any obvious success criteria.
Write in a professional, neutral tone. Do not use markdown headers."""


def _project_report(project) -> str:
    """Generate prompt for project status report."""
    tasks        = project.tasks.all()
    total        = tasks.count()
    done         = tasks.filter(status='done').count()
    in_progress  = tasks.filter(status='in_progress').count()
    overdue      = [t for t in tasks if t.is_overdue]

    return f"""Write a brief project status report (max 200 words) for the following project.
Use a professional tone suitable for a team update email.

Project: {project.name}
Status: {project.get_status_display()}
Due date: {project.due_date or 'Not set'}
Progress: {done}/{total} tasks completed, {in_progress} in progress
Overdue tasks: {len(overdue)}
Description: {project.description or 'No description.'}"""


def _mail_reply(body: str, context: str) -> str:
    """Generate prompt for email reply drafting."""
    return f"""Draft a professional reply to the following email in the context of a project task.
Keep it concise (3-5 sentences). Do not use placeholders like [Name].

Task context: {context}

Original email:
{body[:1500]}"""
