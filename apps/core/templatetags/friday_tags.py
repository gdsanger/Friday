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
