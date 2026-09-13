"""Забирает chat_id из свежих сообщений боту и проставляет пользователям.

Как пользоваться:
  1. Пользователь пишет боту в телеграме команду /start
  2. Администратор запускает: python manage.py fetch_chat_ids
  3. Команда показывает, кто написал, и предлагает связать с аккаунтом

Это самый простой способ узнать chat_id без вебхуков и постоянно
работающего слушателя.
"""

from django.core.management.base import BaseCommand

from notifications.services import TelegramError, get_updates
from users.models import User


class Command(BaseCommand):
    help = 'Показывает chat_id из последних сообщений боту'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            help='Привязать найденный chat_id к пользователю с этим email',
        )

    def handle(self, *args, **options):
        try:
            updates = get_updates()
        except TelegramError as error:
            self.stderr.write(self.style.ERROR(str(error)))
            return

        if not updates:
            self.stdout.write(
                'Свежих сообщений нет. Напишите боту /start и повторите команду.'
            )
            return

        found = {}
        for update in updates:
            message = update.get('message') or {}
            chat = message.get('chat') or {}
            if chat.get('id'):
                found[str(chat['id'])] = chat.get('username') or chat.get('first_name') or '—'

        for chat_id, who in found.items():
            self.stdout.write(f'chat_id={chat_id}  от {who}')

        email = options.get('email')
        if not email:
            self.stdout.write(
                '\nЧтобы привязать: python manage.py fetch_chat_ids --email user@example.com'
            )
            return

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            self.stderr.write(self.style.ERROR(f'Пользователь {email} не найден'))
            return

        chat_id = next(iter(found))
        user.telegram_chat_id = chat_id
        user.save(update_fields=['telegram_chat_id'])
        self.stdout.write(self.style.SUCCESS(f'{email} → chat_id {chat_id}'))
