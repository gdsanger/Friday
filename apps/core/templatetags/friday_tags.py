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
        'planning':  '#4b5563',
        'active':    '#166534',
        'on_hold':   '#92400e',
        'done':      '#1e3a5f',
        'archived':  '#374151',
    }
    return colors.get(project.status, '#4b5563')
