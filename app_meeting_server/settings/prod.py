"""
Django settings for community_meetings project.
Generated by 'django-admin startproject' using Django 2.2.5.
For more information on this file, see
For the full list of settings and their values, see
"""
import ssl
import time
import os
import sys
import yaml
from datetime import timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

CONFIG_PATH = os.getenv('CONFIG_PATH')
MYSQL_TLS_PEM_PATH = os.getenv('MYSQL_TLS_PEM_PATH')

if not os.path.exists(CONFIG_PATH) or not os.path.exists(MYSQL_TLS_PEM_PATH):
    sys.exit()

DEFAULT_CONF = yaml.safe_load(open(CONFIG_PATH, 'r'))
MYSQL_TLS_PEM_CONTENT = open(MYSQL_TLS_PEM_PATH, 'r')

is_delete_config = sys.argv[0] == 'uwsgi' or (len(sys.argv) >= 2 and sys.argv[1] not in ["makemigrations", "migrate"])
if is_delete_config:
    os.remove(CONFIG_PATH)
    os.remove(MYSQL_TLS_PEM_PATH)

# Quick-start development settings - unsuitable for production

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = DEFAULT_CONF.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    DEFAULT_CONF["APP"],
    'rest_framework',
    'corsheaders',
    'django_filters'
]

AUTH_USER_MODEL = DEFAULT_CONF["USER_MODEL"]


CORS_ALLOW_METHODS = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
)
CORS_ALLOW_HEADERS = (
    'XMLHttpRequest',
    'X_FILENAME',
    'accept-encoding',
    'content-type',
    'Authorization',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'Pragma',
)
CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_ALLOW_ALL = True

SESSION_COOKIE_HTTPONLY = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
]

ROOT_URLCONF = 'app_meeting_server.urls'

# common config
ACCESS_KEY_ID = DEFAULT_CONF.get('ACCESS_KEY_ID')
ETHERPAD_PREFIX = DEFAULT_CONF.get('ETHERPAD_PREFIX')
FOR_OPENEULER = DEFAULT_CONF.get('FOR_OPENEULER')
FOR_MINDSPORE = DEFAULT_CONF.get('FOR_MINDSPORE')
COMMUNITY = DEFAULT_CONF.get("COMMUNITY")
MESSAGE_FROM = DEFAULT_CONF.get('MESSAGE_FROM')
OBS_BUCKETNAME = DEFAULT_CONF.get('OBS_BUCKETNAME')
OBS_ENDPOINT = DEFAULT_CONF.get('OBS_ENDPOINT')
PORTAL_EN = DEFAULT_CONF.get('PORTAL_EN')
PORTAL_ZH = DEFAULT_CONF.get('PORTAL_ZH')
QUERY_TOKEN = DEFAULT_CONF.get('QUERY_TOKEN')
SECRET_ACCESS_KEY = DEFAULT_CONF.get('SECRET_ACCESS_KEY')
SMTP_SERVER_SENDER = DEFAULT_CONF.get('SMTP_SERVER_SENDER')
SMTP_SERVER_HOST = DEFAULT_CONF.get('SMTP_SERVER_HOST')
SMTP_SERVER_PASS = DEFAULT_CONF.get('SMTP_SERVER_PASS')
SMTP_SERVER_PORT = DEFAULT_CONF.get('SMTP_SERVER_PORT')
SMTP_SERVER_USER = DEFAULT_CONF.get('SMTP_SERVER_USER')
TENCENT_API_PREFIX = DEFAULT_CONF.get('TENCENT_API_PREFIX')
WELINK_API_PREFIX = DEFAULT_CONF.get('WELINK_API_PREFIX')
WX_API_PREFIX = DEFAULT_CONF.get('WX_API_PREFIX')
ZOOM_API_PREFIX = DEFAULT_CONF.get('ZOOM_API_PREFIX')
CODE_PLATFORM_URL = DEFAULT_CONF.get('CODE_PLATFORM_URL')
VIDEO_PLATFORM_URL = DEFAULT_CONF.get('VIDEO_PLATFORM_URL')
WX_AVATAR_URL = DEFAULT_CONF.get("WX_AVATAR_URL")
REFRESH_SIGNATURE_SECRET = DEFAULT_CONF.get("REFRESH_SIGNATURE_SECRET")
PRIVACY_POLICY_VERSION = DEFAULT_CONF.get('PRIVACY_POLICY_VERSION')
PRIVACY_APP_POLICY_VERSION = DEFAULT_CONF.get('PRIVACY_APP_POLICY_VERSION')
COVER_PATH = DEFAULT_CONF.get("COVER_PATH")
TEMP_PATH = DEFAULT_CONF.get("TEMP_PATH")

WELINK_HOSTS = {
    DEFAULT_CONF.get('WELINK_HOST_1'): {
        'account': DEFAULT_CONF.get('WELINK_HOST_1_ACCOUNT'),
        'pwd': DEFAULT_CONF.get('WELINK_HOST_1_PWD')
    }
}


AES_GCM_SECRET = DEFAULT_CONF.get('AES_GCM_SECRET')
AES_GCM_IV = DEFAULT_CONF.get('AES_GCM_IV')
SIGNATURE_SECRET = DEFAULT_CONF.get('SIGNATURE_SECRET')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=60),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',

}


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

WSGI_APPLICATION = 'app_meeting_server.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DEFAULT_CONF.get('DB_NAME'),
        'USER': DEFAULT_CONF.get('DB_USER'),
        'PASSWORD': DEFAULT_CONF.get('DB_PASSWORD'),
        'HOST': DEFAULT_CONF.get('DB_HOST'),
        'PORT': DEFAULT_CONF.get('DB_PORT'),
        'OPTIONS': {
                'ssl': {
                    'ssl_version': ssl.PROTOCOL_TLSv1_2,
                    'key': MYSQL_TLS_PEM_CONTENT
                },
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

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

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATIC_URL = '/static/'

log_path = os.path.join(os.path.dirname(BASE_DIR), 'logs')

if not os.path.exists(TEMP_PATH):
    os.mkdir(TEMP_PATH)

if not os.path.exists(log_path):
    os.mkdir(log_path)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(module)s:%(funcName)s] '
                      '[%(levelname)s]- %(message)s'},
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'all-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'error-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'info-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        'log': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
    }
}

# logoff expired and clean personal data
LOGOFF_EXPIRED = 6 * 30
ANONYMOUS_NAME = "anonymous"

if FOR_OPENEULER:
    ACCESS_KEY_ID_2 = DEFAULT_CONF.get('ACCESS_KEY_ID_2')
    APP_CONF = {
        'appid': DEFAULT_CONF.get('APP_ID'),
        'secret': DEFAULT_CONF.get('APP_SECRET')
    }
    BILI_JCT = DEFAULT_CONF.get('BILI_JCT')
    BILI_UID = DEFAULT_CONF.get('BILI_UID')
    BUCKET_NAME = DEFAULT_CONF.get('BUCKET_NAME')
    CANCEL_MEETING_TEMPLATE = DEFAULT_CONF.get('CANCEL_MEETING_TEMPLATE')
    CI_BOT_TOKEN = DEFAULT_CONF.get('CI_BOT_TOKEN')
    COMMUNITY_REPO_URL = DEFAULT_CONF.get('COMMUNITY_REPO_URL')
    ENDPOINT = DEFAULT_CONF.get('ENDPOINT')
    GITEE_V5_API_PREFIX = DEFAULT_CONF.get('GITEE_V5_API_PREFIX')
    MAILLIST_API = DEFAULT_CONF.get('MAILLIST_API')
    MEETING_ATTENTION_TEMPLATE = DEFAULT_CONF.get('MEETING_ATTENTION_TEMPLATE')
    MEETING_HOSTS = {
        'zoom': {
            DEFAULT_CONF.get('NEW_HOST_1'): DEFAULT_CONF.get('HOST_1_ACCOUNT'),
            DEFAULT_CONF.get('NEW_HOST_2'): DEFAULT_CONF.get('HOST_2_ACCOUNT'),
            DEFAULT_CONF.get('NEW_HOST_3'): DEFAULT_CONF.get('HOST_3_ACCOUNT'),
            DEFAULT_CONF.get('NEW_HOST_4'): DEFAULT_CONF.get('HOST_4_ACCOUNT')
        },
        'welink': {
            DEFAULT_CONF.get('WELINK_HOST_1'): DEFAULT_CONF.get('WELINK_HOST_1')
        },
        'tencent': {
            DEFAULT_CONF.get('TENCENT_ACCOUNT_1'): DEFAULT_CONF.get('TENCENT_ACCOUNT_1'),
            DEFAULT_CONF.get('TENCENT_ACCOUNT_2'): DEFAULT_CONF.get('TENCENT_ACCOUNT_2')
        }
    }
    OBJ_KEY = DEFAULT_CONF.get('OBJ_KEY')
    OBS_BUCKETNAME_2 = DEFAULT_CONF.get('OBS_BUCKETNAME_2')
    OBS_BUCKETNAME_SECOND = DEFAULT_CONF.get('OBS_BUCKETNAME_SECOND')
    OBS_ENDPOINT_2 = DEFAULT_CONF.get('OBS_ENDPOINT_2')
    QUERY_INTERVAL = DEFAULT_CONF.get('QUERY_INTERVAL')
    SECRET_ACCESS_KEY_2 = DEFAULT_CONF.get('SECRET_ACCESS_KEY_2')
    SESSDATA = DEFAULT_CONF.get('SESSDATA')
    SIGS_INFO_OBJECT = DEFAULT_CONF.get('SIGS_INFO_OBJECT')
    TENCENT_HOST_KEY = DEFAULT_CONF.get('TENCENT_HOST_KEY')
    TX_MEETING_APPID = DEFAULT_CONF.get('TX_MEETING_APPID')
    TX_MEETING_SECRETID = DEFAULT_CONF.get('TX_MEETING_SECRETID')
    TX_MEETING_SECRETKEY = DEFAULT_CONF.get('TX_MEETING_SECRETKEY')
    TX_MEETING_SDKID = DEFAULT_CONF.get('TX_MEETING_SDKID')
    ZOOM_TOKEN_OBJECT = DEFAULT_CONF.get('ZOOM_TOKEN_OBJECT')

elif FOR_MINDSPORE:
    APP_CONF = {
        'appid': DEFAULT_CONF.get('APP_ID'),
        'secret': DEFAULT_CONF.get('APP_SECRET')
    }
    CANCEL_MEETING_TEMPLATE = DEFAULT_CONF.get('CANCEL_MEETING_TEMPLATE')
    COMMUNITY_REPO_URL = DEFAULT_CONF.get('COMMUNITY_REPO_URL')
    MEETING_ATTENTION_TEMPLATE = DEFAULT_CONF.get('MEETING_ATTENTION_TEMPLATE')
    MEETING_HOSTS = {
        'tencent': ['TENCENT_ACCOUNT_1'],
        'welink': [DEFAULT_CONF.get('WELINK_HOST_1')]
    }
    QUERY_AK = DEFAULT_CONF.get('QUERY_AK')
    QUERY_BUCKETNAME = DEFAULT_CONF.get('QUERY_BUCKETNAME')
    QUERY_ENDPOINT = DEFAULT_CONF.get('QUERY_ENDPOINT')
    QUERY_INTERVAL = DEFAULT_CONF.get('QUERY_INTERVAL')
    QUERY_OBJ = DEFAULT_CONF.get('QUERY_OBJ')
    QUERY_SK = DEFAULT_CONF.get('QUERY_SK')
    TENCENT_HOST_KEY = DEFAULT_CONF.get('TENCENT_HOST_KEY')
    TX_MEETING_APPID = DEFAULT_CONF.get('TX_MEETING_APPID')
    TX_MEETING_SDKID = DEFAULT_CONF.get('TX_MEETING_SDKID')
    TX_MEETING_SECRETKEY = DEFAULT_CONF.get('TX_MEETING_SECRETKEY')
    TX_MEETING_SECRETID = DEFAULT_CONF.get('TX_MEETING_SECRETID')

DEFAULT_CONF = None
MYSQL_TLS_PEM_CONTENT = None
