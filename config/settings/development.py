"""
Development settings for Friday project.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver','friday.isarlabs.de']

# Print emails to console instead of sending
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# No HTTPS required locally
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Disable HSTS in development
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
