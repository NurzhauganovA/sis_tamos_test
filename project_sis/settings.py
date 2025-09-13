import os
from datetime import timedelta
from pathlib import Path
import environ
from celery.schedules import crontab

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, 'docker/dev/envs/.env.sis_backend.dev'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # if DEBUG else environ.get('ALLOWED_HOSTS')
# print(f'AllowedHosts : {ALLOWED_HOSTS}')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'secret_key' if DEBUG else env('SECRET_KEY')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',
    'rest_framework_simplejwt',
    'djoser',
    'django.contrib.staticfiles',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'corsheaders',
    'django_filters',

    'django_celery_beat',

    'apps.user',
    'apps.school',
    'apps.dish',
    'apps.statement',
    'apps.student',
    'apps.sms',
    'apps.contract',
    'apps.driver',
    'apps.payment',

    'django_seed',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project_sis.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project_sis.wsgi.application'

ASGI_APPLICATION = 'project_sis.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    },
    'ms_sql': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': env('MS_DB_NAME'),
        'HOST': env('MS_DB_HOST'),
        'PORT': env('MS_DB_PORT'),
        'USER': env('MS_DB_USER'),
        'PASSWORD': env('MS_DB_PASSWORD'),
        'OPTIONS': {
            "driver": "FreeTDS",
            "host_is_server": True,
            "unicode_results": True,
            "extra_params": "tds_version=7.4",
        }
    }
}


MIGRATION_MODULES = {}

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

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Asia/Almaty'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'user.User'


REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 'apps._parent.jwt.CustomJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS':
        'drf_spectacular.openapi.AutoSchema',
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append('rest_framework.renderers.BrowsableAPIRenderer')

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# DJOSER = {
#     'PASSWORD_RESET_CONFIRM_URL': '#/password/reset/confirm/{uid}/{token}',
#     'USERNAME_RESET_CONFIRM_URL': '#/username/reset/confirm/{uid}/{token}',
#     'ACTIVATION_URL': 'api/v1/_parent/activation/{uid}/{token}',
#     'SEND_ACTIVATION_EMAIL': True,
#     'SEND_CONFIRMATION_EMAIL': True,
#     'SERIALIZERS': {
#         "user_create": "apps._parent.serializers.SimpleUserSerializer",
#     },
#     'PERMISSIONS': {
#         "user_list": ["apps._parent.permissions.IsAdmin"],
#     },
# }

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('JWT',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SIS API',
    'DESCRIPTION': 'SIS API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    'COMPONENT_SPLIT_REQUEST': True,

    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR'
}

SMS_CREDENTIALS = {
    'LOGIN': env('SMS_LOGIN'),
    'PASSWORD': env('SMS_PASSWORD'),
    'SENDER': env('SMS_SENDER')
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{env("REDIS_HOST")}:{env("REDIS_PORT")}/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


CORS_ORIGIN_WHITELIST = env.list('CORS_ORIGIN_WHITELIST')  # [] if DEBUG else environ.get('CORS_ORIGIN_WHITELIST')
CORS_ORIGIN_ALLOW_ALL = env.bool('CORS_ORIGIN_ALLOW_ALL')  # False if DEBUG else environ.get('CORS_ORIGIN_ALLOW_ALL')
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS')  # False if DEBUG else environ.get('CORS_ALLOW_CREDENTIALS')
CORS_ALLOW_HEADERS = env.list('CORS_ALLOW_HEADERS')  # [] if DEBUG else environ.get('CORS_ALLOW_HEADERS')


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media_files')


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Celery settings
CELERY_BROKER_URL = f'redis://{env("REDIS_HOST")}:{env("REDIS_PORT")}/0'
CELERY_RESULT_BACKEND = f'redis://{env("REDIS_HOST")}:{env("REDIS_PORT")}/0'

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CELERY_TIMEZONE = env('CELERY_TIMEZONE')
CELERY_BEAT_SCHEDULE = env('CELERY_BEAT_SCHEDULE')

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 # 10 Mb limit

EDS_OMAROV_KEY = env('EDS_OMAROV_KEY')
EDS_SERIKOV_KEY = env('EDS_SERIKOV_KEY')

AITU_PASSPORT_SETTINGS = {
    "TEST_BASE_URL": "",
    "PROD_BASE_URL": "",
    "CLIENT_ID": "",
    "CLIENT_SECRET": "",
    "REDIRECT_URI": "",
    "USE_TEST": True
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'contract_signatures.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.contract': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}