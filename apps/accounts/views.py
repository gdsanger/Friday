"""
Accounts app views.
"""
from __future__ import annotations

import secrets
from urllib.parse import urlencode
from datetime import timedelta

import msal
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from apps.mail.models import UserMailToken


def _build_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=f'https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}',
    )

def _msal_authorization_scopes() -> list[str]:
    """
    Scopes for the authorization URL (step 1 of OAuth flow).
    Includes reserved OIDC scopes to ensure we get an id_token with stable identity claims.
    """
    scopes = ['openid', 'profile', 'email'] + list(settings.MSAL_SCOPES)
    # Deduplicate while preserving order.
    return list(dict.fromkeys(scopes))

def _msal_token_scopes() -> list[str]:
    """
    Scopes for token acquisition (step 2 of OAuth flow).
    Excludes reserved scopes (openid, profile, offline_access) as MSAL validates against these.
    Reserved scopes are automatically handled by MSAL when present in authorization URL.
    """
    reserved_scopes = {'openid', 'profile', 'offline_access', 'email'}
    scopes = [s for s in settings.MSAL_SCOPES if s not in reserved_scopes]
    return scopes


class AzureLoginView(View):
    """Initiate MSAL Auth Code Flow — redirect user to Microsoft login."""

    def get(self, request):
        state = secrets.token_urlsafe(16)
        request.session['azure_auth_state'] = state
        tenant = settings.AZURE_TENANT_ID or 'common'
        authorize_endpoint = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize'
        params = {
            'client_id': settings.AZURE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.AZURE_REDIRECT_URI,
            'response_mode': 'query',
            'scope': ' '.join(_msal_authorization_scopes()),
            'state': state,
            'nonce': state,
        }
        return redirect(f'{authorize_endpoint}?{urlencode(params)}')


class AzureCallbackView(View):
    """Handle Microsoft callback, acquire tokens, map to Django user."""

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        state = request.GET.get('state')

        expected_state = request.session.get('azure_auth_state')
        request.session.pop('azure_auth_state', None)

        if not expected_state or not state or state != expected_state:
            return render(request, 'accounts/login.html', {'error': 'Azure login failed: invalid state.'})

        if error or not code:
            return render(
                request,
                'accounts/login.html',
                {'error': f'Azure login failed: {request.GET.get("error_description", error)}'},
            )

        msal_app = _build_msal_app()
        result = msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=_msal_token_scopes(),
            redirect_uri=settings.AZURE_REDIRECT_URI,
        )

        if 'error' in result:
            return render(
                request,
                'accounts/login.html',
                {'error': result.get('error_description', 'Token acquisition failed.')},
            )

        claims = result.get('id_token_claims', {}) or {}
        azure_oid = claims.get('oid', '') or ''
        email = claims.get('preferred_username', '') or claims.get('email', '') or ''
        name = claims.get('name', '') or ''
        upn = claims.get('upn', email) or email

        if not azure_oid:
            return render(
                request,
                'accounts/login.html',
                {'error': 'Could not retrieve user identity from Microsoft.'},
            )

        User = get_user_model()
        user = User.objects.filter(azure_oid=azure_oid).first()

        if not user:
            username = (email.split('@')[0] if email else '') or azure_oid[:30]
            base_username = username[:150]  # Django's default max_length for username
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                suffix = str(counter)
                username = (base_username[: max(1, 150 - len(suffix))] + suffix)
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                azure_oid=azure_oid,
                azure_upn=upn,
                display_name=name,
            )
            user.set_unusable_password()
            user.save()
        else:
            changed_fields: list[str] = []
            if name and getattr(user, 'display_name', '') != name:
                user.display_name = name
                changed_fields.append('display_name')
            if email and getattr(user, 'email', '') != email:
                user.email = email
                changed_fields.append('email')
            if upn and getattr(user, 'azure_upn', '') != upn:
                user.azure_upn = upn
                changed_fields.append('azure_upn')
            if changed_fields:
                user.save(update_fields=changed_fields)

        UserMailToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token', ''),
                'expires_at': timezone.now() + timedelta(seconds=result.get('expires_in', 3600)),
                'scopes': (result.get('scope', '') or '').split(),
            },
        )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(settings.LOGIN_REDIRECT_URL)


class StandardLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
        return render(request, self.template_name, {'error': 'Invalid username or password.'})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.notify_email = request.POST.get('notify_email') == 'on'
        user.notify_inapp = request.POST.get('notify_inapp') == 'on'
        user.timezone = (request.POST.get('timezone') or user.timezone).strip() or user.timezone
        user.save(update_fields=['notify_email', 'notify_inapp', 'timezone'])
        return redirect('accounts:profile')

    teams = getattr(request.user, 'teams', None)
    return render(
        request,
        'accounts/profile.html',
        {
            'teams': teams.all() if hasattr(teams, 'all') else teams,
        },
    )
