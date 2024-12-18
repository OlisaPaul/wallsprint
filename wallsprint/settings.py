"""
Django settings for wallsprint project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api


# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['wallsprint.onrender.com', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django_filters",
    'rest_framework',
    'djoser',
    'debug_toolbar',
    'core',
    'store',
    'corsheaders'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RoleBasedAccessMiddleware'
]

ROOT_URLCONF = 'wallsprint.urls'

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

WSGI_APPLICATION = 'wallsprint.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wallsprint',
        'HOST': os.getenv('MYSQL_HOST'),
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('PASSWORD')
    }
}
DATABASE_URL = os.getenv('DATABASE_URL')
WORK_ENV = os.getenv('WORK_ENV')

if WORK_ENV != 'develop':
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "core.User"

REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': False,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

DJOSER = {
    "SERIALIZERS": {
        # 'password_reset': 'core.serializers.CustomPasswordResetSerializer',
        "user_create": 'core.serializers.UserCreateSerializer',
        "current_user": 'core.serializers.UpdateCurrentUserSerializer',
        "user": 'core.serializers.UserSerializer',
        'token_create': 'core.serializers.CustomTokenCreateSerializer',
        'user_delete': 'core.serializers.CustomUserDeleteSerializer',
    },
    'EMAIL': {
        'password_reset': 'core.email.CustomPasswordResetEmail',
    },
    'PERMISSIONS': {
        "user_create": ['rest_framework.permissions.IsAdminUser'],
    },
    'DOMAIN': 'wallsprint.netlify.app',
    'SITE_NAME': 'Wallsprint',
    'PASSWORD_RESET_CONFIRM_URL': 'reset-password/{uid}/{token}',
    'PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    # 'SEND_ACTIVATION_EMAIL': True,
    # 'ACTIVATION_URL': 'reset-password/{uid}/{token}',
    # 'SEND_CONFIRMATION_EMAIL': True,
    'LOGIN_FIELD': 'email',
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER')

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=int(os.getenv('ACCESS_TOKEN_LIFETIME'))),
    'AUTH_HEADER_TYPES': ('Bearer',)
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET')
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CORS_ALLOW_ALL_ORIGINS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

DOMAIN = 'wallsprint.netlify.app'
SITE_NAME = 'Wallsprint'
