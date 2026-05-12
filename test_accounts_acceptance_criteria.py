#!/usr/bin/env python
"""
Test script to verify acceptance criteria for ISSUE-05 (Accounts & Azure SSO).

This script focuses on:
- Login page renders both standard + Microsoft options
- Standard login success/failure behavior
- Azure login redirect + Azure callback error handling
- Azure callback maps azure_oid to User and stores UserMailToken
- Logout requires POST and redirects to login
- Profile page requires login and allows preference updates
"""

import os
import sys
from unittest.mock import patch


def _setup_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    os.environ.setdefault('DATABASE_URL', 'sqlite:////tmp/friday_issue05.sqlite3')
    os.environ.setdefault('FIELD_ENCRYPTION_KEY', '9RpaVfMK_6gwyMBlycIzeKORhY5_iBCh53-uL4eK74I=')

    import django
    django.setup()

    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
    call_command('flush', interactive=False, verbosity=0)

    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')


_setup_django()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.mail.models import UserMailToken

User = get_user_model()


def test_login_page_renders_both_options():
    client = Client()
    res = client.get('/accounts/login/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    body = res.content.decode()
    assert 'Sign in with Microsoft' in body, "Microsoft SSO button not present"
    assert 'csrfmiddlewaretoken' in body, "CSRF token missing from standard login form"
    print("✓ GET /accounts/login/ renders standard + Microsoft login options")


def test_standard_login_success_and_failure():
    client = Client()

    user = User.objects.create_user(username='issue05_user', email='u@example.com', password='pw12345')

    bad = client.post('/accounts/login/', {'username': user.username, 'password': 'wrong'})
    assert bad.status_code == 200, f"Expected 200, got {bad.status_code}"
    assert 'Invalid username or password.' in bad.content.decode(), "Expected invalid-credentials error"

    good = client.post('/accounts/login/', {'username': user.username, 'password': 'pw12345'})
    assert good.status_code in (301, 302), f"Expected redirect, got {good.status_code}"
    assert good['Location'].endswith(settings.LOGIN_REDIRECT_URL), \
        f"Expected redirect to {settings.LOGIN_REDIRECT_URL}, got {good['Location']}"

    print("✓ Standard login redirects on success, renders error on failure")


def test_azure_login_redirects_to_microsoft():
    client = Client()
    # Ensure redirect URI is correct for test client host
    settings.AZURE_REDIRECT_URI = 'http://testserver/accounts/azure/callback/'
    settings.AZURE_CLIENT_ID = settings.AZURE_CLIENT_ID or '00000000-0000-0000-0000-000000000000'
    settings.AZURE_TENANT_ID = settings.AZURE_TENANT_ID or 'common'

    res = client.get('/accounts/azure/login/')
    assert res.status_code in (301, 302), f"Expected redirect, got {res.status_code}"
    assert 'login.microsoftonline.com' in res['Location'], "Azure login redirect does not target Microsoft"
    print("✓ GET /accounts/azure/login/ redirects to login.microsoftonline.com")


def test_azure_callback_error_renders_login_with_error():
    client = Client()
    session = client.session
    session['azure_auth_state'] = 'state-123'
    session.save()

    res = client.get('/accounts/azure/callback/', {'state': 'state-123', 'error': 'access_denied', 'error_description': 'Denied'})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert 'Azure login failed:' in res.content.decode(), "Expected Azure error message on login page"
    print("✓ Failed Azure callback renders login page with error")


def test_successful_azure_callback_creates_user_and_token_and_updates():
    client = Client()
    settings.AZURE_REDIRECT_URI = 'http://testserver/accounts/azure/callback/'

    class FakeMsalApp:
        def acquire_token_by_authorization_code(self, **kwargs):
            return {
                'access_token': 'access-token-1',
                'refresh_token': 'refresh-token-1',
                'expires_in': 3600,
                'scope': 'User.Read Mail.Send',
                'id_token_claims': {
                    'oid': 'oid-abc',
                    'preferred_username': 'first@example.com',
                    'name': 'First User',
                    'upn': 'first@example.com',
                },
            }

    # First login creates user + token
    session = client.session
    session['azure_auth_state'] = 'state-xyz'
    session.save()

    with patch('apps.accounts.views._build_msal_app', return_value=FakeMsalApp()):
        res = client.get('/accounts/azure/callback/', {'state': 'state-xyz', 'code': 'code-1'})
    assert res.status_code in (301, 302), f"Expected redirect, got {res.status_code}"
    assert res['Location'].endswith(settings.LOGIN_REDIRECT_URL), "Expected redirect to dashboard after Azure login"

    user = User.objects.filter(azure_oid='oid-abc').first()
    assert user is not None, "User not created on first Azure login"
    assert user.email == 'first@example.com', "User email not set from Azure claims"
    assert user.display_name == 'First User', "User display_name not set from Azure claims"

    token = UserMailToken.objects.filter(user=user).first()
    assert token is not None, "UserMailToken not created"
    assert token.access_token == 'access-token-1', "Access token not stored"

    # Second login updates user fields, no duplicate user
    class FakeMsalApp2:
        def acquire_token_by_authorization_code(self, **kwargs):
            return {
                'access_token': 'access-token-2',
                'refresh_token': 'refresh-token-2',
                'expires_in': 3600,
                'scope': 'User.Read Mail.Send',
                'id_token_claims': {
                    'oid': 'oid-abc',
                    'preferred_username': 'second@example.com',
                    'name': 'Second Name',
                    'upn': 'second@example.com',
                },
            }

    session = client.session
    session['azure_auth_state'] = 'state-xyz2'
    session.save()

    with patch('apps.accounts.views._build_msal_app', return_value=FakeMsalApp2()):
        res2 = client.get('/accounts/azure/callback/', {'state': 'state-xyz2', 'code': 'code-2'})
    assert res2.status_code in (301, 302), f"Expected redirect, got {res2.status_code}"

    assert User.objects.filter(azure_oid='oid-abc').count() == 1, "Duplicate user created for same azure_oid"
    user.refresh_from_db()
    assert user.email == 'second@example.com', "User email not updated on subsequent Azure login"
    assert user.display_name == 'Second Name', "User display_name not updated on subsequent Azure login"

    token.refresh_from_db()
    assert token.access_token == 'access-token-2', "Token not updated on subsequent Azure login"

    print("✓ Successful Azure callback creates/updates User and UserMailToken using azure_oid")


def test_logout_requires_post_and_redirects():
    client = Client()
    user = User.objects.create_user(username='logout_user', email='lo@example.com', password='pw12345')
    assert client.login(username=user.username, password='pw12345') is True, "Precondition failed: could not log in"

    get_res = client.get('/accounts/logout/')
    assert get_res.status_code == 405, f"Expected 405 for GET logout, got {get_res.status_code}"

    post_res = client.post('/accounts/logout/')
    assert post_res.status_code in (301, 302), f"Expected redirect, got {post_res.status_code}"
    assert post_res['Location'].endswith(settings.LOGOUT_REDIRECT_URL), \
        f"Expected redirect to {settings.LOGOUT_REDIRECT_URL}, got {post_res['Location']}"

    print("✓ POST /accounts/logout/ logs out and redirects to login")


def test_profile_requires_login_and_updates_preferences():
    client = Client()

    anon = client.get('/accounts/profile/')
    assert anon.status_code in (301, 302), f"Expected redirect, got {anon.status_code}"
    assert settings.LOGIN_URL in anon['Location'], "Expected redirect to LOGIN_URL for anonymous profile access"

    user = User.objects.create_user(username='profile_user', email='p@example.com', password='pw12345')
    assert client.login(username=user.username, password='pw12345') is True, "Precondition failed: could not log in"

    res = client.get('/accounts/profile/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert 'Preferences' in res.content.decode(), "Profile page missing preferences section"

    post = client.post('/accounts/profile/', {'notify_email': 'on', 'timezone': 'UTC'})
    assert post.status_code in (301, 302), f"Expected redirect, got {post.status_code}"

    user.refresh_from_db()
    assert user.notify_email is True, "notify_email not updated"
    assert user.timezone == 'UTC', "timezone not updated"

    print("✓ GET /accounts/profile/ requires login; POST updates preferences")


def run_all_tests():
    print("\n" + "=" * 70)
    print("ISSUE-05 Acceptance Criteria Tests (Accounts & Azure SSO)")
    print("=" * 70 + "\n")

    tests = [
        test_login_page_renders_both_options,
        test_standard_login_success_and_failure,
        test_azure_login_redirects_to_microsoft,
        test_azure_callback_error_renders_login_with_error,
        test_successful_azure_callback_creates_user_and_token_and_updates,
        test_logout_requires_post_and_redirects,
        test_profile_requires_login_and_updates_preferences,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")

    if failed == 0:
        print("🎉 All ISSUE-05 tests passed!")
        return 0
    print("❌ Some ISSUE-05 tests failed")
    return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
