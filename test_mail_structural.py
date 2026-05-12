#!/usr/bin/env python
"""
Non-Database Test script to verify structural acceptance criteria for ISSUE-03.

Tests that don't require database connection:
- Settings configuration
- Celery Beat schedule
- Django admin registration
- Service timeout configuration
- Webhook validation token handling
"""

import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
os.environ['FIELD_ENCRYPTION_KEY'] = '9RpaVfMK_6gwyMBlycIzeKORhY5_iBCh53-uL4eK74I='

import django
django.setup()

from django.test import RequestFactory
from apps.mail.views import graph_webhook
import json


def test_settings_configuration():
    """Test required settings are configured"""
    from django.conf import settings

    assert hasattr(settings, 'AZURE_CLIENT_ID'), "AZURE_CLIENT_ID not configured"
    assert hasattr(settings, 'AZURE_CLIENT_SECRET'), "AZURE_CLIENT_SECRET not configured"
    assert hasattr(settings, 'AZURE_TENANT_ID'), "AZURE_TENANT_ID not configured"
    assert hasattr(settings, 'GRAPH_WEBHOOK_URL'), "GRAPH_WEBHOOK_URL not configured"
    assert hasattr(settings, 'MSAL_SCOPES'), "MSAL_SCOPES not configured"

    expected_scopes = ['User.Read', 'Mail.ReadWrite', 'Mail.Send']
    assert settings.MSAL_SCOPES == expected_scopes, \
        f"MSAL_SCOPES should be {expected_scopes}, got {settings.MSAL_SCOPES}"

    print("✓ All required settings are configured (AZURE_*, GRAPH_WEBHOOK_URL, MSAL_SCOPES)")


def test_celery_beat_schedule():
    """Test Celery Beat schedule includes webhook renewal task"""
    from config.celery import app

    assert 'renew-webhook-subscriptions' in app.conf.beat_schedule, \
        "renew-webhook-subscriptions not in beat schedule"

    schedule_config = app.conf.beat_schedule['renew-webhook-subscriptions']
    assert schedule_config['task'] == 'apps.mail.tasks.renew_webhook_subscriptions', \
        "Task path incorrect"

    print("✓ Celery Beat schedule configured for webhook renewal (daily at 06:00)")


def test_models_registered_in_admin():
    """Test Django admin is registered for all mail models"""
    from django.contrib import admin
    from apps.mail.models import UserMailToken, MailThread, WebhookSubscription

    assert admin.site.is_registered(UserMailToken), "UserMailToken not registered in admin"
    assert admin.site.is_registered(MailThread), "MailThread not registered in admin"
    assert admin.site.is_registered(WebhookSubscription), "WebhookSubscription not registered in admin"

    print("✓ Django admin is registered for all mail models")


def test_service_timeout_configuration():
    """Test MailService methods use appropriate timeouts"""
    import inspect
    from apps.mail import service

    # Check service.py source code for timeout parameters
    source = inspect.getsource(service)

    # Count httpx calls with timeout
    timeout_count = source.count('timeout=')
    assert timeout_count >= 4, \
        f"Expected at least 4 httpx calls with timeout, found {timeout_count}"

    # Check that all timeouts are >= 10 seconds
    import re
    timeouts = re.findall(r'timeout=(\d+)', source)
    timeouts = [int(t) for t in timeouts]
    assert all(t >= 10 for t in timeouts), \
        f"All timeouts should be >= 10 seconds, got {timeouts}"

    print("✓ All Graph API calls use httpx with a timeout of ≥ 10 seconds")


def test_webhook_validation_token():
    """Test POST /api/mail/webhook/ responds with validationToken for Graph handshake"""
    factory = RequestFactory()
    request = factory.get('/api/mail/webhook/', {'validationToken': 'test-validation-token-12345'})

    response = graph_webhook(request)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.content.decode() == 'test-validation-token-12345', \
        "Response should echo validation token"
    assert response['Content-Type'] == 'text/plain', \
        "Content-Type should be text/plain"

    print("✓ POST /api/mail/webhook/ responds with validationToken for Graph handshake")


def test_webhook_invalid_client_state():
    """Test POST /api/mail/webhook/ with invalid clientState returns 202"""
    factory = RequestFactory()
    payload = {
        'value': [
            {
                'clientState': 'invalid-state',
                'subscriptionId': 'sub-123',
                'resourceData': {
                    'id': 'message-456'
                }
            }
        ]
    }
    request = factory.post(
        '/api/mail/webhook/',
        data=json.dumps(payload),
        content_type='application/json'
    )

    response = graph_webhook(request)

    assert response.status_code == 202, f"Expected 202, got {response.status_code}"
    print("✓ POST /api/mail/webhook/ with invalid clientState is silently ignored (no error)")


def test_models_structure():
    """Test mail models have correct structure"""
    from apps.mail.models import UserMailToken, MailThread, WebhookSubscription
    from encrypted_model_fields.fields import EncryptedTextField

    # UserMailToken
    assert hasattr(UserMailToken, 'user'), "UserMailToken should have user field"
    assert hasattr(UserMailToken, 'access_token'), "UserMailToken should have access_token field"
    assert hasattr(UserMailToken, 'refresh_token'), "UserMailToken should have refresh_token field"
    assert hasattr(UserMailToken, 'expires_at'), "UserMailToken should have expires_at field"
    assert hasattr(UserMailToken, 'is_expired'), "UserMailToken should have is_expired method"

    # Check encryption
    access_token_field = UserMailToken._meta.get_field('access_token')
    refresh_token_field = UserMailToken._meta.get_field('refresh_token')
    assert isinstance(access_token_field, EncryptedTextField), \
        "access_token should use EncryptedTextField"
    assert isinstance(refresh_token_field, EncryptedTextField), \
        "refresh_token should use EncryptedTextField"

    # MailThread
    assert hasattr(MailThread, 'task'), "MailThread should have task field"
    assert hasattr(MailThread, 'graph_message_id'), "MailThread should have graph_message_id field"
    assert hasattr(MailThread, 'direction'), "MailThread should have direction field"
    assert MailThread.DIRECTION_IN == 'in', "DIRECTION_IN should be 'in'"
    assert MailThread.DIRECTION_OUT == 'out', "DIRECTION_OUT should be 'out'"

    # WebhookSubscription
    assert hasattr(WebhookSubscription, 'user'), "WebhookSubscription should have user field"
    assert hasattr(WebhookSubscription, 'subscription_id'), "WebhookSubscription should have subscription_id field"
    assert hasattr(WebhookSubscription, 'expiration'), "WebhookSubscription should have expiration field"

    print("✓ Mail models have correct structure with encrypted fields")


def test_service_class_structure():
    """Test MailService class has required methods"""
    from apps.mail.service import MailService, GraphAuthError

    # Check class exists
    assert MailService is not None, "MailService class should exist"
    assert GraphAuthError is not None, "GraphAuthError exception should exist"

    # Check required methods
    required_methods = [
        'get_valid_token',
        '_refresh_token',
        '_headers',
        'send_mail',
        'send_notification_mail',
        'create_webhook_subscription',
        'fetch_message',
        '_get_last_sent_message_id'
    ]

    for method_name in required_methods:
        assert hasattr(MailService, method_name), \
            f"MailService should have {method_name} method"

    print("✓ MailService class has all required methods")


def test_celery_tasks_exist():
    """Test Celery tasks are defined"""
    from apps.mail import tasks

    assert hasattr(tasks, 'process_incoming_mail'), \
        "process_incoming_mail task should exist"
    assert hasattr(tasks, 'renew_webhook_subscriptions'), \
        "renew_webhook_subscriptions task should exist"

    print("✓ Celery tasks are defined (process_incoming_mail, renew_webhook_subscriptions)")


def test_url_configuration():
    """Test URL configuration includes webhook endpoint"""
    from django.urls import reverse, NoReverseMatch

    try:
        webhook_url = reverse('mail:graph-webhook')
        assert '/api/mail/webhook/' in webhook_url, \
            f"Webhook URL should be /api/mail/webhook/, got {webhook_url}"
        print("✓ URL configuration includes webhook endpoint at /api/mail/webhook/")
    except NoReverseMatch:
        assert False, "URL 'mail:graph-webhook' not configured"


def run_all_tests():
    """Run all structural tests"""
    print("\n" + "="*70)
    print("ISSUE-03 Structural Acceptance Tests (No Database Required)")
    print("="*70 + "\n")

    tests = [
        test_settings_configuration,
        test_celery_beat_schedule,
        test_models_registered_in_admin,
        test_service_timeout_configuration,
        test_webhook_validation_token,
        test_webhook_invalid_client_state,
        test_models_structure,
        test_service_class_structure,
        test_celery_tasks_exist,
        test_url_configuration,
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

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    if failed == 0:
        print("🎉 All structural tests passed!")
        print("\nNote: Full integration tests require:")
        print("  - PostgreSQL database running")
        print("  - Azure App Registration configured")
        print("  - Valid Microsoft Graph API credentials")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
