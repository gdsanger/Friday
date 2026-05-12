"""
Context processors for Friday project.
Provides global template variables.
"""


def friday_context(request):
    """
    Add Friday-specific context variables to all templates.
    """
    context = {
        'app_version': '1.0.0',
        'user_teams': [],
    }

    # Add user teams if authenticated
    if request.user.is_authenticated:
        try:
            context['user_teams'] = list(request.user.teams.all()) if hasattr(request.user, 'teams') else []
        except Exception:
            # Teams model may not be available yet
            context['user_teams'] = []

    return context
