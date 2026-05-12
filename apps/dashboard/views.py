"""
Dashboard views.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    """Dashboard home page."""
    return render(request, 'dashboard/index.html', {
        'user': request.user,
    })
