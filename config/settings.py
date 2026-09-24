"""Настройки проекта «Трекер привычек».

Все секреты и параметры окружения читаются из .env — образец лежит
в .env.template. В репозиторий .env не попадает.
"""

import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_list(name: str, default: str = '') -> list[str]:
    """Читает из окружения список, записанный через запятую."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me-in-env')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    'corsheaders',

    # Наши
    'users',
    'habits',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # CorsMiddleware должен стоять как можно выше и обязательно
    # до CommonMiddleware, иначе заголовки не попадут в ответ
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'


# База данных

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = os.getenv('TIME_ZONE', 'Europe/Vienna')

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'

# Куда collectstatic складывает файлы. На сервере этот каталог примонтирован
# томом, из которого их читает Nginx: Python не должен отдавать картинки и CSS
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'


# DRF: по умолчанию всё закрыто, аутентификация по JWT,
# пагинация limit/offset с выдачей по пять привычек на страницу.

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'habits.paginators.HabitPaginator',
    'PAGE_SIZE': 5,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('ACCESS_TOKEN_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('REFRESH_TOKEN_DAYS', 1))),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Трекер полезных привычек',
    'DESCRIPTION': (
        'Бэкенд SPA-приложения по мотивам книги «Атомные привычки». '
        'Привычки, публичная витрина и напоминания в Telegram.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'TAGS': [
        {'name': 'auth', 'description': 'Регистрация и JWT-токены'},
        {'name': 'habits', 'description': 'Привычки пользователя'},
        {'name': 'public', 'description': 'Публичная витрина привычек'},
        {'name': 'users', 'description': 'Профиль пользователя'},
    ],
}


# CORS: фронтенд живёт на другом домене, без этих настроек
# браузер заблокирует запросы к API.

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000',
)
CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000',
)
CORS_ALLOW_CREDENTIALS = True


# Celery

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Таймзоны Django и Celery обязаны совпадать, иначе напоминания
# будут приходить не в то время, которое выбрал пользователь.
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = USE_TZ

CELERY_BEAT_SCHEDULE = {
    'send-habit-reminders-every-minute': {
        'task': 'notifications.tasks.send_habit_reminders',
        'schedule': crontab(minute='*'),
    },
}


# Telegram

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_URL = os.getenv('TELEGRAM_API_URL', 'https://api.telegram.org/bot')

# Сколько ждать ответа от Telegram. Десяти секунд хватает не всегда:
# на медленном канале запрос обрывается на полпути, хотя сервис жив.
TELEGRAM_TIMEOUT_SECONDS = int(os.getenv('TELEGRAM_TIMEOUT_SECONDS', 30))

# Насколько широкое окно считается «временем привычки».
# Beat запускается раз в минуту, но если воркер был занят или лежал,
# напоминание не должно пропасть совсем.
REMINDER_WINDOW_MINUTES = int(os.getenv('REMINDER_WINDOW_MINUTES', 5))
