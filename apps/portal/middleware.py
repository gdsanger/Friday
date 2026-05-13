"""Portal user middleware to restrict access."""
from django.shortcuts import redirect


class PortalUserMiddleware:
    """Middleware to restrict portal users to portal-only URLs."""

    PORTAL_PATHS = (
        '/portal/',
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/azure/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.user.is_authenticated
                and request.user.is_portal_user
                and not any(request.path.startswith(p)
                            for p in self.PORTAL_PATHS)):
            return redirect('portal-home')
        return self.get_response(request)
