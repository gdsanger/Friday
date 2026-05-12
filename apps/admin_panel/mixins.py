"""
Admin panel mixins for access control.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin):
    """All admin panel views require is_staff=True."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
