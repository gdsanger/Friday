"""
Notification views for Friday project.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from .models import Notification


class NotificationListView(LoginRequiredMixin, View):
    """
    Display all notifications for the current user.
    Mark all as read when visiting the page.
    """
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('actor').order_by('-created_at')

        # Mark all as read on page visit
        notifications.filter(is_read=False).update(is_read=True)

        return render(request, 'notifications/list.html', {
            'notifications': notifications[:50],
        })


class NotificationMarkReadView(LoginRequiredMixin, View):
    """HTMX — mark single notification as read, return updated row."""
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return render(request, 'notifications/partials/notification_row.html',
                      {'notification': notif})


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """HTMX — mark all as read, return updated unread count (0) for topbar badge."""
    def post(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return render(request, 'notifications/partials/unread_count.html',
                      {'unread_count': 0})
