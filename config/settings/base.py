"""
Django settings for Friday project.
Base settings file - shared configuration.
"""
from pathlib import Path
import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Application definition
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    # Third-party
    'django_htmx',
    # Friday apps
    'apps.core',
    'apps.accounts',
    'apps.teams',
    'apps.projects',
    'apps.tasks',
    'apps.kanban',
    'apps.dashboard',
    'apps.mail',
    'apps.ai',
    'apps.notifications',
    'apps.admin_panel',
    'apps.portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'apps.portal.middleware.PortalUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.friday_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://localhost/friday')
}

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = env('MEDIA_URL', default='/media/')
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Redis Configuration
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# Azure / MSAL Configuration
AZURE_CLIENT_ID = env('AZURE_CLIENT_ID', default='')
AZURE_CLIENT_SECRET = env('AZURE_CLIENT_SECRET', default='')
AZURE_TENANT_ID = env('AZURE_TENANT_ID', default='common')
AZURE_REDIRECT_URI = env('AZURE_REDIRECT_URI', default='http://localhost:8000/accounts/azure/callback/')

# Graph API
GRAPH_WEBHOOK_URL = env('GRAPH_WEBHOOK_URL', default='')
MSAL_SCOPES = ['User.Read', 'Mail.ReadWrite', 'Mail.Send']

# Mail Service (separate from SSO) — Client Credentials Flow
MAIL_AZURE_CLIENT_ID = env('MAIL_AZURE_CLIENT_ID', default='')
MAIL_AZURE_CLIENT_SECRET = env('MAIL_AZURE_CLIENT_SECRET', default='')
MAIL_AZURE_TENANT_ID = env('MAIL_AZURE_TENANT_ID', default='common')
MAIL_FROM_ADDRESS = env('MAIL_FROM_ADDRESS', default='friday@isartec.de')
MAIL_FROM_NAME = env('MAIL_FROM_NAME', default='Friday')
MAIL_SHARED_MAILBOX = env('MAIL_SHARED_MAILBOX', default='friday@isartec.de')
SITE_URL = env('SITE_URL', default='http://localhost:8011')

# AI Configuration (used for initial seeding only)
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
OPENAI_MODEL = env('OPENAI_MODEL', default='gpt-4o')
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
ANTHROPIC_MODEL = env('ANTHROPIC_MODEL', default='claude-sonnet-4-20250514')
AI_DEFAULT_PROVIDER = env('AI_DEFAULT_PROVIDER', default='openai')
AI_FALLBACK_PROVIDER = env('AI_FALLBACK_PROVIDER', default='claude')

# Field Encryption
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')
