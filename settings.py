##
#    Copyright (C) 2014 Jessica Tallon & Matt Molyneaux
#
#    This file is part of Inboxen.
#
#    Inboxen is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Inboxen is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with Inboxen  If not, see <http://www.gnu.org/licenses/>.
##

import datetime
import os

from django.contrib.messages import constants as message_constants
from django.core import exceptions, urlresolvers

import configobj
import validate

import djcelery
djcelery.setup_loader()

##
# Most configuration can be done via settings.ini
#
# The file is searched for in the follow way:
# 1. The environment variable "INBOXEN_CONFIG", which contains an absolute path
# 2. ~/.config/inboxen/settings.ini
# 3. settings.ini in the same folder as this file
#
# See inboxen/config_spec.ini for defaults, see below for comments
##

# Shorthand for Django's default database backends
db_dict = {
            "postgresql": "django.db.backends.postgresql_psycopg2",
            "mysql": "django.db.backends.mysql",
            "oracle": "django.db.backends.oracle",
            "sqlite": "django.db.backends.sqlite3"
            }

BASE_DIR = os.path.dirname(__file__)

if os.path.exists(os.getenv('INBOX_CONFIG', '')):
    CONFIG_PATH = os.getenv('INBOX_CONFIG')
elif os.path.exists(os.path.expanduser("~/.config/inboxen/settings.ini")):
    CONFIG_PATH = os.path.expanduser("~/.config/inboxen/settings.ini")
elif os.path.exists(os.path.join(BASE_DIR, "settings.ini")):
    CONFIG_PATH = os.path.join(BASE_DIR, "settings.ini")
else:
    raise exceptions.ImproperlyConfigured("You must provide a settings.ini file")

config_spec = os.path.join(BASE_DIR, "inboxen/config_spec.ini")

config = configobj.ConfigObj(CONFIG_PATH, configspec=config_spec)
config.validate(validate.Validator())

# TODO: These could be merged into a custom validator
try:
    SECRET_KEY = config["general"]["secret_key"]
except KeyError:
    raise exceptions.ImproperlyConfigured("You must set 'secret_key' in your settings.ini")

if len(config["general"]["admin_names"]) != len(config["general"]["admin_emails"]):
    raise exceptions.ImproperlyConfigured("You must have the same number of admin_names as admin_emails settings.ini")

# Admins (and managers)
ADMINS = zip(config["general"]["admin_names"], config["general"]["admin_emails"])

# List of hosts allowed
ALLOWED_HOSTS = config["general"]["allowed_hosts"]

# Enable debugging - DO NOT USE IN PRODUCTION
DEBUG = config["general"]["debug"]

# Alloew new users to register
ENABLE_REGISTRATION = config["general"]["enable_registration"]

# Cooloff time, in minutes, for failed logins
LOGIN_ATTEMPT_COOLOFF = config["general"]["login_attempt_cooloff"]

# Maximum number of unsuccessful login attempts
LOGIN_ATTEMPT_LIMIT = config["general"]["login_attempt_limit"]

# Language code, e.g. en-gb
LANGUAGE_CODE = config["general"]["language_code"]

# Email the server uses when sending emails
SERVER_EMAIL = config["general"]["server_email"]

# Site name used in page titles
SITE_NAME = config["general"]["site_name"]

# Where `manage.py collectstatic` puts static files
STATIC_ROOT = os.path.join(BASE_DIR, config["general"]["static_root"])

# Time zone
TIME_ZONE = config["general"]["time_zone"]

# Length of the local part (bit before the @) of autogenerated inbox addresses
INBOX_LENGTH = config["inbox"]["inbox_length"]

# Maximum number of free inboxes before a request for more will be generated
MIN_INBOX_FOR_REQUEST = config["inbox"]["min_inbox_for_request"]

# Increase the pool amount by this number when a user request is granted
REQUEST_NUMBER = config["inbox"]["request_number"]

# Where Celery looks for new tasks and stores results
BROKER_URL = config["tasks"]["broker_url"]

# Number of Celery processes to start
CELERYD_CONCURRENCY = config["tasks"]["concurrency"]

# Path where liberation data is temporarily stored
LIBERATION_PATH = os.path.join(BASE_DIR, config["tasks"]["liberation"]["path"])


# Databases!
DATABASES = {
    'default': {
        'ENGINE': db_dict[config["database"]["engine"]],
        'USER': config["database"]["user"],
        'PASSWORD': config["database"]["password"],
        'HOST': config["database"]["host"],
        'PORT': config["database"]["port"],
    }
}

# "name" is a path for sqlite databases
if config["database"]["engine"] == "sqlite":
    DATABASES["default"]["NAME"] = os.path.join(BASE_DIR, config["database"]["name"])
else:
    DATABASES["default"]["NAME"] = config["database"]["name"]

##
# To override the following settings, create a separate settings module.
# Import this module, override what you need to and set the environment
# variable DJANGO_SETTINGS_MODULE to your module. See Django docs for details
##

if not DEBUG:
    # These security settings are annoying while debugging
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


CELERY_RESULT_BACKEND = BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERYBEAT_SCHEDULE = {
    'statistics':{
        'task':'queue.tasks.statistics',
        'schedule':datetime.timedelta(hours=6),
    },
    'cleanup':{
        'task':'queue.delete.tasks.clean_orphan_models',
        'schedule':datetime.timedelta(hours=2),
    },
}

# if you change this, you'll need to do a datamigration to change the rest
COLUMN_HASHER = "sha1"

MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

TEMPLATE_DEBUG = DEBUG

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

AUTHENTICATION_BACKENDS = (
    'website.backends.RateLimitWithSettings',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'inboxen_cache'),
    }
}

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "website.context_processors.reduced_settings_context"
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'async_messages.middleware.AsyncMiddleware',
    'website.middleware.RateLimitMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'django_extensions',
    'djcelery',
    'inboxen',
    'website',
    'queue',
    'queue.delete',
    'queue.liberate',
)

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar',)

ROOT_URLCONF = 'website.urls'

LOGIN_URL = urlresolvers.reverse_lazy("user-login")
LOGOUT_URL = urlresolvers.reverse_lazy("user-logout")
LOGIN_REDIRECT_URL = urlresolvers.reverse_lazy("user-home")

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'website.wsgi.application'