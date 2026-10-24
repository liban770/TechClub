"""
Django settings for techclub_core project.
Configured for TechClub with PostgreSQL, Tailwind CSS tokens, and modular apps.
"""

from pathlib import Path
import os

import importlib

try:
    dj_database_url = importlib.import_module('dj_database_url')
except ImportError:
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-techclub-som-secret-key-2025-hargeisa')

# In production (e.g. Vercel), default DEBUG to False for security. Locally default to True.
_default_debug = 'False' if ('VERCEL' in os.environ or os.environ.get('ENVIRONMENT') == 'production') else 'True'
DEBUG = os.environ.get('DJANGO_DEBUG', os.environ.get('DEBUG', _default_debug)).lower() in ('true', '1')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver,.vercel.app,techclub-platform.vercel.app').split(',') if h.strip()]

# Automatic Vercel & Render.com hostname binding
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

vercel_url = os.environ.get('VERCEL_URL')
if vercel_url and vercel_url not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(vercel_url)

if '.vercel.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.vercel.app')
if 'techclub-platform.vercel.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('techclub-platform.vercel.app')

if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(['127.0.0.1', 'localhost', 'testserver'])
ALLOWED_HOSTS = list(set(ALLOWED_HOSTS))

# CSRF Trusted Origins (HTTPS support for production & Vercel)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS', 
        'http://127.0.0.1:8000,http://localhost:8000,https://techclub-platform.vercel.app,https://*.vercel.app'
    ).split(',') if origin.strip()
]
if render_hostname:
    render_origin = f"https://{render_hostname}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

if vercel_url:
    vercel_origin = f"https://{vercel_url}"
    if vercel_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(vercel_origin)

for host in ALLOWED_HOSTS:
    if host not in ('127.0.0.1', 'localhost', 'testserver', '*'):
        if host.startswith('.'):
            wildcard_origin = f"https://*{host}"
            if wildcard_origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(wildcard_origin)
        else:
            https_origin = f"https://{host}"
            if https_origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(https_origin)
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # TechClub Custom Applications
    'accounts.apps.AccountsConfig',
    'applications.apps.ApplicationsConfig',
    'members.apps.MembersConfig',
    'events.apps.EventsConfig',
    'meetings.apps.MeetingsConfig',
    'announcements.apps.AnnouncementsConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'techclub_core.urls'

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
                'dashboard.context_processors.global_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'techclub_core.wsgi.application'

# Database Configuration (PostgreSQL locally or DATABASE_URL in cloud: Neon, Supabase, Vercel)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()

if DATABASE_URL and dj_database_url:
    # Managed Cloud PostgreSQL (Neon, Supabase, Render, Railway, AWS RDS)
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=('neon.tech' in DATABASE_URL or 'supabase' in DATABASE_URL or 'sslmode=require' in DATABASE_URL or not DEBUG),
        )
    }
elif 'VERCEL' in os.environ:
    # Serverless preview fallback on Vercel when DATABASE_URL is not yet added in project settings
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/tmp/db.sqlite3',
        }
    }
elif dj_database_url:
    default_db_url = f"postgresql://{os.environ.get('DB_USER', 'techclub')}:{os.environ.get('DB_PASSWORD', 'techclub_pass')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'techclub_db')}"
    DATABASES = {
        'default': dj_database_url.config(
            default=default_db_url,
            conn_max_age=600,
            ssl_require=os.environ.get('DB_SSL_REQUIRE', 'False').lower() in ('true', '1'),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'techclub_db'),
            'USER': os.environ.get('DB_USER', 'techclub'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'techclub_pass'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Strict Password Validation Suite (OWASP Standard)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Session & Cookie Security (Defense against Session Hijacking & XSS Cookie Theft)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400 * 14  # 14 days
SESSION_SAVE_EVERY_REQUEST = True

# Browser Security Headers (Defense against Clickjacking, MIME-sniffing, XSS)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# File Upload Memory & Size Constraints (Defense against Disk Exhaustion DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Reverse Proxy & Cloud SSL Headers (Vercel, Render, Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Production HTTPS Hardening
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year HSTS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Mogadishu'  # EAT (UTC+3)
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Production Static Asset Storage with WhiteNoise
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# User-Uploaded Media files (Persistent Storage)
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
SERVE_MEDIA_FILES = os.environ.get('SERVE_MEDIA_FILES', 'True').lower() in ('true', '1')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_dispatch'
LOGOUT_REDIRECT_URL = 'home'

# Email backend: console by default for local testing, SMTP configurable via environment variables
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'admissions@techclub.so')
