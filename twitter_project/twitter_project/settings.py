"""
Django settings for twitter_project project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
print("PROJECT PATH IS")
print(PROJECT_PATH)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'eo-#h-_vhx9)w#7=70+3_p*5h=fd$&wf9hpm&a-xht+t1iaw81'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'twitter',
    'gunicorn',
)
SOUTH_AUTO_FREEZE_APP = True

dependencies = [
    ('contenttypes', '__first__'),
    ('twitter', '0001'),
    ('twitter', '0002'),
    ('twitter', '0003'),
    ('twitter', '0004'),
]

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'twitter_project.urls'

WSGI_APPLICATION = 'twitter_project.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
)

AUTH_PROFILE_MODULE = 'twitter.userprofile'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_PATH = os.path.join(PROJECT_PATH, 'static')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_PATH,'static')


STATICFILES_DIRS = (
    STATIC_PATH,
)

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_PATH,'media')

