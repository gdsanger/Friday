"""Portal mixins for view access control."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PortalUserRequiredMixin(LoginRequiredMixin):
    """Mixin to require portal user authentication."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_portal_user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
