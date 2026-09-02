import logging
import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a local .env file if present.
# This keeps development defaults out of the source tree.
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv:
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)


def _env_list(name, default=None, sep=','):
    value = os.environ.get(name, '')
    if not value:
        return default or []
    return [item.strip() for item in value.split(sep) if item.strip()]


DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Development fallback so you don't have to generate one every time.
        # NEVER use this value in production or expose it outside your network.
        SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production'
        warnings.warn(
            "使用内置开发 SECRET_KEY。生产环境请设置强随机密钥！",
            RuntimeWarning,
            stacklevel=2,
        )
    else:
        raise ImproperlyConfigured("环境变量 SECRET_KEY 必须设置")

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS')
if DEBUG:
    # 开发模式下允许任意 Host 访问（方便局域网内其他设备调用 Mock）
    ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'common',
    'api',
    'schedule',
    'mock',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ROOT_URLCONF = 'apitester.urls'

WSGI_APPLICATION = 'apitester.wsgi.application'

DB_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'db.sqlite3'))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_PATH,
    }
}

# ---- Cache ----
# Used by DRF rate-limiting (ScopedRateThrottle) and Django's cache framework.
#
# LocMemCache is **in-process** — under multi-worker deployments (Uvicorn
# --workers N) each worker keeps its own counter, so rate limits become
# N × configured_rate instead of the configured_rate itself.
#
# For accurate cross-worker rate limiting, set REDIS_URL and switch to:
#   'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#   'LOCATION': os.environ['REDIS_URL'],
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'apitester-throttle',
        }
    }

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = False
USE_TZ = True

# ---- Logging (local timezone) ----
class LocalTimeFormatter(logging.Formatter):
    """Formatter that uses local time instead of UTC."""

    def formatTime(self, record, datefmt=None):
        local = datetime.fromtimestamp(record.created)
        if datefmt:
            return local.strftime(datefmt)
        return local.strftime('%Y-%m-%d %H:%M:%S')


LOG_DIR = Path(os.environ.get('LOG_DIR', BASE_DIR / 'logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'local': {
            '()': 'apitester.settings.LocalTimeFormatter',
            'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s',
        },
        'verbose': {
            '()': 'apitester.settings.LocalTimeFormatter',
            'format': '[%(asctime)s] %(levelname)s %(name)s %(pathname)s:%(lineno)d %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'local',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': os.environ.get('ERROR_LOG', str(LOG_DIR / 'errors.log')),
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'app_file': {
            'class': 'logging.FileHandler',
            'filename': os.environ.get('APP_LOG', str(LOG_DIR / 'app.log')),
            'formatter': 'local',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'app_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'schedule': {
            'handlers': ['console', 'app_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- Third-party settings ----
CORS_ALLOWED_ORIGINS = _env_list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://127.0.0.1:5173'] if DEBUG else []
)
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'UNAUTHENTICATED_USER': None,
    'EXCEPTION_HANDLER': 'apitester.exception_handler.unified_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'proxy': '60/min',
        'curl': '120/min',
        'kafka': '60/min',
        'rocketmq': '60/min',
        'collections': '200/hour',
        'environments': '200/hour',
        'history': '1000/hour',
        'schedule': '300/min',
        'mock': '200/hour',
        'mock_serve': '30/min',
        'auth_register': '60/hour',
        'auth_login': '20/min',
        'auth_refresh': '60/min',
    },
}

# ---- JWT Configuration ----
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---- Proxy (SSRF) hardening ----
# When True, the proxy is allowed to target private/loopback addresses
# (e.g. http://127.0.0.1 during local development). Leave False in shared/
# production deployments to avoid SSRF to internal services.
API_PROXY_ALLOW_PRIVATE = os.environ.get('API_PROXY_ALLOW_PRIVATE', '0') == '1'

# ---- Security hardening (only effective when SSL is terminated by Django) ----
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', '1') == '1'
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

