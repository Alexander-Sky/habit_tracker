"""Инстанс Celery.

Импортируется в config/__init__.py, чтобы приложение поднималось вместе
с Django — без этого задачи не зарегистрируются.
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Все настройки Celery живут в settings.py с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Ищет tasks.py во всех приложениях из INSTALLED_APPS
app.autodiscover_tasks()
