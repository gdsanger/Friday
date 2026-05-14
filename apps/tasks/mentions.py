"""
Mention parsing and rendering for task comments.
Handles @username mentions in comment text.
"""
import re
from django.contrib.auth import get_user_model


def parse_mentions(text: str) -> list:
    """
    Find all @username mentions in text and return User objects.

    Args:
        text: Comment body text containing @username mentions

    Returns:
        List of User objects for valid, active, non-portal users mentioned

    Example:
        >>> parse_mentions("@john please review this @jane")
        [<User: john>, <User: jane>]
    """
    User = get_user_model()
    pattern = r'@([\w.+-]+)'
    usernames = re.findall(pattern, text)

    if not usernames:
        return []

    # Filter to active, non-portal users only
    return list(
        User.objects.filter(
            username__in=usernames,
            is_active=True,
            is_portal_user=False,
        ).distinct()
    )


def render_mentions(text: str) -> str:
    """
    Replace @username in text with HTML span for UI highlighting.

    Args:
        text: Raw comment text with @username mentions

    Returns:
        HTML string with mentions wrapped in <span class="mention">

    Example:
        >>> render_mentions("@john please review")
        '<span class="mention">@john</span> please review'
    """
    pattern = r'@([\w.+-]+)'
    return re.sub(
        pattern,
        r'<span class="mention">@\1</span>',
        text
    )
