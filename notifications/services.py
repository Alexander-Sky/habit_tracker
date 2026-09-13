"""Работа с Telegram Bot API.

Всё общение с мессенджером собрано здесь. Задачи и вьюхи не знают,
как устроен телеграм: если завтра добавится другой канал уведомлений,
переписывать придётся только этот файл.

Документация: https://core.telegram.org/bots/api
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Телеграм не принял сообщение."""


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Отправляет сообщение в чат. Возвращает True, если телеграм принял.

    Токен не задан — молча ничего не делаем: так проект запускается
    и без бота, а разработчик видит предупреждение в логе.

    https://core.telegram.org/bots/api#sendmessage
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning('TELEGRAM_BOT_TOKEN не задан — сообщение не отправлено')
        return False

    if not chat_id:
        logger.warning('У пользователя нет telegram_chat_id — сообщение не отправлено')
        return False

    url = f'{settings.TELEGRAM_API_URL}{settings.TELEGRAM_BOT_TOKEN}/sendMessage'

    try:
        response = requests.post(
            url,
            data={'chat_id': chat_id, 'text': text},
            timeout=settings.TELEGRAM_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        logger.warning('Не удалось связаться с Telegram: %s', error)
        return False

    if response.status_code != 200:
        logger.warning(
            'Telegram отклонил сообщение для чата %s: %s %s',
            chat_id, response.status_code, response.text[:200],
        )
        return False

    return True


def get_updates(offset: int | None = None) -> list[dict]:
    """Забирает свежие сообщения бота — чтобы узнать chat_id пользователя.

    Используется вспомогательной командой manage.py fetch_chat_ids.

    https://core.telegram.org/bots/api#getupdates
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramError('TELEGRAM_BOT_TOKEN не задан')

    url = f'{settings.TELEGRAM_API_URL}{settings.TELEGRAM_BOT_TOKEN}/getUpdates'
    params = {'offset': offset} if offset else {}

    try:
        response = requests.get(url, params=params, timeout=settings.TELEGRAM_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        # Иначе наружу летит голый трейсбек urllib3 — команде это ни о чём
        # не говорит, а причина у всех таких ошибок одна: сеть
        raise TelegramError(f'Не удалось связаться с Telegram: {error}') from error

    if response.status_code != 200:
        raise TelegramError(f'Telegram вернул {response.status_code}: {response.text[:200]}')

    return response.json().get('result', [])
