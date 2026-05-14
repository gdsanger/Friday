"""
Template tags and filters for Friday project.
"""
from django import template

register = template.Library()


@register.filter
def file_icon(filename):
    """Return Bootstrap icon name based on file extension."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    icons = {
        'pdf':                          'bi-file-earmark-pdf',
        'doc':  'bi-file-earmark-word', 'docx': 'bi-file-earmark-word',
        'xls':  'bi-file-earmark-excel','xlsx': 'bi-file-earmark-excel',
        'ppt':  'bi-file-earmark-ppt',  'pptx': 'bi-file-earmark-ppt',
        'png':  'bi-file-earmark-image','jpg':  'bi-file-earmark-image',
        'jpeg': 'bi-file-earmark-image','gif':  'bi-file-earmark-image',
        'zip':  'bi-file-earmark-zip',  'tar':  'bi-file-earmark-zip',
        'py':   'bi-file-earmark-code', 'js':   'bi-file-earmark-code',
        'html': 'bi-file-earmark-code', 'css':  'bi-file-earmark-code',
        'txt':  'bi-file-earmark-text', 'md':   'bi-file-earmark-text',
    }
    return icons.get(ext, 'bi-file-earmark')


@register.filter
def subtract(value, arg):
    """{{ total|subtract:open }}"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def status_color(project):
    """Return a muted background color for project status badges."""
    colors = {
        'planning':     '#4b5563',  # grau
        'active':       '#166534',  # grün
        'on_hold':      '#92400e',  # amber
        'production':   '#1e3a5f',  # dunkelblau
        'done':         '#1e3a5f',  # dunkelblau
        'deferred':     '#6b21a8',  # lila
        'archived':     '#374151',  # dunkelgrau
        'end_of_life':  '#374151',  # dunkelgrau
    }
    return colors.get(project.status, '#4b5563')


@register.filter
def priority_icon(priority):
    """Return Bootstrap icon name for a priority value."""
    icons = {
        4: 'bi-exclamation-circle-fill',
        3: 'bi-exclamation-triangle-fill',
        2: 'bi-dash-circle-fill',
        1: 'bi-arrow-down-circle',
        0: '',
    }
    try:
        return icons.get(int(priority), '')
    except (ValueError, TypeError):
        return ''


@register.filter
def priority_color(priority):
    """Return CSS color for a priority value."""
    colors = {
        4: '#e55039',
        3: '#f4a261',
        2: '#6b7280',
        1: '#6b7280',
        0: '',
    }
    try:
        return colors.get(int(priority), '')
    except (ValueError, TypeError):
        return ''


@register.filter
def subtask_count(task):
    """Return total count of subtasks for a task."""
    try:
        return task.subtasks.count()
    except (AttributeError, TypeError):
        return 0


@register.filter
def done_subtask_count(task):
    """Return count of completed subtasks for a task."""
    try:
        return task.subtasks.filter(status='done').count()
    except (AttributeError, TypeError):
        return 0


@register.filter
def get_item(dictionary, key):
    """{{ post|get_item:'field_name' }}"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key, '')
    return ''


@register.filter
def getlist(post_data, key):
    """{{ post|getlist:'field_name' }} — für Multiselect"""
    if hasattr(post_data, 'getlist'):
        return post_data.getlist(key)
    return []


@register.filter
def highlight_mentions(text):
    """
    Replace @username with HTML span for highlighting in comments.
    Example: @john -> <span class="mention">@john</span>
    """
    import re
    return re.sub(
        r'@([\w.+-]+)',
        r'<span class="mention">@\1</span>',
        text
    )
