"""
HTML Mail Template Renderer for Friday Mail Engine.
"""
from django.template.loader import render_to_string
from django.conf import settings


def render_mail_template(template_name: str, context: dict) -> str:
    """
    Render a mail template from templates/mail/<template_name>.html.
    Automatically adds base context variables (app_name, from_address, etc.)

    Args:
        template_name: Template filename without .html extension, e.g. 'task_assigned'
        context: Template context dictionary

    Returns:
        Rendered HTML string
    """
    base_context = {
        'app_name': 'Friday',
        'app_url': settings.SITE_URL,
        'from_name': settings.MAIL_FROM_NAME,
        'from_address': settings.MAIL_FROM_ADDRESS,
        'support_url': f'{settings.SITE_URL}/portal/',
    }
    base_context.update(context)

    return render_to_string(
        f'mail/{template_name}.html',
        base_context,
    )
