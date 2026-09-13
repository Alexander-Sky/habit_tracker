from datetime import time, timedelta
from io import StringIO
from unittest.mock import patch

import requests
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from habits.models import Habit
from notifications.services import TelegramError, get_updates, send_telegram_message
from notifications.tasks import build_reminder_text, is_due, send_habit_reminders
from users.models import User

TOKEN = '123456:test-token'


class FakeResponse:
    """Подделка ответа requests: у настоящего есть и код, и текст."""

    def __init__(self, status_code=200, text='{"ok": true}'):
        self.status_code = status_code
        self.text = text
        self._json = {'ok': True, 'result': []}

    def json(self):
        return self._json


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class SendTelegramMessageTestCase(TestCase):
    """Отправка сообщения в телеграм."""

    def test_message_is_sent(self):
        with patch('notifications.services.requests.post', return_value=FakeResponse()) as mocked:
            result = send_telegram_message('123', 'Пора гулять')

        self.assertTrue(result)
        url, = mocked.call_args.args
        self.assertIn('sendMessage', url)
        self.assertEqual(mocked.call_args.kwargs['data']['chat_id'], '123')
        self.assertEqual(mocked.call_args.kwargs['data']['text'], 'Пора гулять')

    def test_token_is_in_url_not_in_body(self):
        with patch('notifications.services.requests.post', return_value=FakeResponse()) as mocked:
            send_telegram_message('123', 'текст')

        url, = mocked.call_args.args
        self.assertIn(TOKEN, url)

    def test_telegram_error_returns_false(self):
        response = FakeResponse(status_code=400, text='{"ok": false}')

        with patch('notifications.services.requests.post', return_value=response):
            self.assertFalse(send_telegram_message('123', 'текст'))

    def test_network_error_returns_false(self):
        with patch('notifications.services.requests.post',
                   side_effect=requests.RequestException('нет сети')):
            self.assertFalse(send_telegram_message('123', 'текст'))

    @override_settings(TELEGRAM_TIMEOUT_SECONDS=42)
    def test_timeout_comes_from_settings(self):
        with patch('notifications.services.requests.post', return_value=FakeResponse()) as mocked:
            send_telegram_message('123', 'текст')

        self.assertEqual(mocked.call_args.kwargs['timeout'], 42)

    def test_empty_chat_id_returns_false(self):
        with patch('notifications.services.requests.post') as mocked:
            self.assertFalse(send_telegram_message('', 'текст'))

        mocked.assert_not_called()


class TelegramWithoutTokenTestCase(TestCase):
    """Без токена проект должен работать, просто не слать сообщения."""

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_send_returns_false(self):
        with patch('notifications.services.requests.post') as mocked:
            self.assertFalse(send_telegram_message('123', 'текст'))

        mocked.assert_not_called()

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_get_updates_raises(self):
        with self.assertRaises(TelegramError):
            get_updates()


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class GetUpdatesTestCase(TestCase):
    """Чтение входящих сообщений бота."""

    def test_returns_result_list(self):
        response = FakeResponse()
        response._json = {'ok': True, 'result': [{'message': {'chat': {'id': 42}}}]}

        with patch('notifications.services.requests.get', return_value=response):
            updates = get_updates()

        self.assertEqual(updates[0]['message']['chat']['id'], 42)

    def test_bad_status_raises(self):
        with patch('notifications.services.requests.get', return_value=FakeResponse(status_code=401)):
            with self.assertRaises(TelegramError):
                get_updates()

    def test_network_error_becomes_telegram_error(self):
        """Сетевой сбой не должен вылетать голым трейсбеком urllib3."""
        with patch('notifications.services.requests.get',
                   side_effect=requests.ReadTimeout('read timed out')):
            with self.assertRaises(TelegramError) as context:
                get_updates()

        self.assertIn('read timed out', str(context.exception))

    @override_settings(TELEGRAM_TIMEOUT_SECONDS=42)
    def test_timeout_comes_from_settings(self):
        with patch('notifications.services.requests.get', return_value=FakeResponse()) as mocked:
            get_updates()

        self.assertEqual(mocked.call_args.kwargs['timeout'], 42)


class ReminderTextTestCase(TestCase):
    """Текст напоминания."""

    def setUp(self):
        self.user = User.objects.create(email='user@test.ru', telegram_chat_id='123')

    def test_reward_is_mentioned(self):
        habit = Habit.objects.create(
            user=self.user, action='гулять', time=time(19, 0), place='парк', reward='десерт',
        )
        text = build_reminder_text(habit)

        self.assertIn('гулять', text)
        self.assertIn('парк', text)
        self.assertIn('десерт', text)

    def test_related_habit_is_mentioned(self):
        pleasant = Habit.objects.create(
            user=self.user, action='принять ванну', time=time(21, 0),
            place='дома', is_pleasant=True,
        )
        habit = Habit.objects.create(
            user=self.user, action='гулять', time=time(19, 0),
            place='парк', related_habit=pleasant,
        )

        self.assertIn('принять ванну', build_reminder_text(habit))

    def test_habit_without_reward(self):
        habit = Habit.objects.create(
            user=self.user, action='гулять', time=time(19, 0), place='парк',
        )
        text = build_reminder_text(habit)

        self.assertIn('гулять', text)
        self.assertNotIn('Награда', text)


class IsDueTestCase(TestCase):
    """Периодичность: когда пора напоминать снова."""

    def setUp(self):
        self.user = User.objects.create(email='user@test.ru', telegram_chat_id='123')
        self.now = timezone.localtime()

    def _habit(self, periodicity=1, last=None):
        return Habit.objects.create(
            user=self.user, action='гулять', time=time(19, 0), place='парк',
            periodicity=periodicity, last_reminded_at=last,
        )

    def test_first_reminder_is_always_due(self):
        self.assertTrue(is_due(self._habit(), self.now))

    def test_daily_habit_is_due_next_day(self):
        habit = self._habit(periodicity=1, last=self.now - timedelta(days=1, minutes=1))
        self.assertTrue(is_due(habit, self.now))

    def test_daily_habit_is_not_due_same_day(self):
        habit = self._habit(periodicity=1, last=self.now - timedelta(hours=2))
        self.assertFalse(is_due(habit, self.now))

    def test_three_day_habit_waits_three_days(self):
        habit = self._habit(periodicity=3, last=self.now - timedelta(days=2))
        self.assertFalse(is_due(habit, self.now))

        habit.last_reminded_at = self.now - timedelta(days=3, minutes=1)
        self.assertTrue(is_due(habit, self.now))


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class SendHabitRemindersTestCase(TestCase):
    """Периодическая задача рассылки."""

    def setUp(self):
        self.now = timezone.localtime()
        self.user = User.objects.create(email='user@test.ru', telegram_chat_id='123')
        self.habit = Habit.objects.create(
            user=self.user, action='гулять', time=self.now.time(), place='парк',
        )

    def test_reminder_is_sent(self):
        with patch('notifications.tasks.send_telegram_message', return_value=True) as mocked:
            sent = send_habit_reminders()

        self.assertEqual(sent, 1)
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.args[0], '123')

    def test_last_reminded_at_is_updated(self):
        with patch('notifications.tasks.send_telegram_message', return_value=True):
            send_habit_reminders()

        self.habit.refresh_from_db()
        self.assertIsNotNone(self.habit.last_reminded_at)

    def test_failed_send_does_not_mark_as_reminded(self):
        """Телеграм не ответил — попробуем в следующий раз."""
        with patch('notifications.tasks.send_telegram_message', return_value=False):
            sent = send_habit_reminders()

        self.habit.refresh_from_db()
        self.assertEqual(sent, 0)
        self.assertIsNone(self.habit.last_reminded_at)

    def test_user_without_chat_id_is_skipped(self):
        self.user.telegram_chat_id = ''
        self.user.save()

        with patch('notifications.tasks.send_telegram_message') as mocked:
            self.assertEqual(send_habit_reminders(), 0)

        mocked.assert_not_called()

    def test_inactive_user_is_skipped(self):
        self.user.is_active = False
        self.user.save()

        with patch('notifications.tasks.send_telegram_message') as mocked:
            self.assertEqual(send_habit_reminders(), 0)

        mocked.assert_not_called()

    def test_habit_at_another_time_is_skipped(self):
        self.habit.time = (self.now - timedelta(hours=3)).time()
        self.habit.save()

        with patch('notifications.tasks.send_telegram_message') as mocked:
            self.assertEqual(send_habit_reminders(), 0)

        mocked.assert_not_called()

    def test_recently_reminded_habit_is_skipped(self):
        self.habit.last_reminded_at = self.now - timedelta(hours=1)
        self.habit.save()

        with patch('notifications.tasks.send_telegram_message') as mocked:
            self.assertEqual(send_habit_reminders(), 0)

        mocked.assert_not_called()

    @override_settings(REMINDER_WINDOW_MINUTES=5)
    def test_habit_exactly_on_window_edge_is_included(self):
        """Привычка на самой границе окна не должна теряться.

        У привычки время ровное, у границы окна — с микросекундами.
        Без округления 05:02:00 оказывается «раньше» 05:02:00.005.
        """
        edge = (self.now - timedelta(minutes=5)).time().replace(microsecond=0)
        self.habit.time = edge
        self.habit.save()

        with patch('notifications.tasks.send_telegram_message', return_value=True):
            self.assertEqual(send_habit_reminders(), 1)

    @override_settings(REMINDER_WINDOW_MINUTES=5)
    def test_window_covers_recent_past(self):
        """Воркер был занят пару минут — напоминание всё равно уйдёт."""
        self.habit.time = (self.now - timedelta(minutes=3)).time()
        self.habit.save()

        with patch('notifications.tasks.send_telegram_message', return_value=True):
            self.assertEqual(send_habit_reminders(), 1)


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class FetchChatIdsCommandTestCase(TestCase):
    """Команда, которая узнаёт chat_id из сообщений боту."""

    def setUp(self):
        self.user = User.objects.create(email='user@test.ru')
        self.updates = [{'message': {'chat': {'id': 987654321, 'username': 'alex'}}}]

    def _run(self, **options):
        out = StringIO()
        err = StringIO()
        call_command('fetch_chat_ids', stdout=out, stderr=err, **options)
        return out.getvalue(), err.getvalue()

    def test_shows_found_chat_ids(self):
        with patch('notifications.management.commands.fetch_chat_ids.get_updates',
                   return_value=self.updates):
            out, _ = self._run()

        self.assertIn('987654321', out)
        self.assertIn('alex', out)

    def test_binds_chat_id_to_user(self):
        with patch('notifications.management.commands.fetch_chat_ids.get_updates',
                   return_value=self.updates):
            self._run(email='user@test.ru')

        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, '987654321')

    def test_unknown_email_reports_error(self):
        with patch('notifications.management.commands.fetch_chat_ids.get_updates',
                   return_value=self.updates):
            _, err = self._run(email='nobody@test.ru')

        self.assertIn('не найден', err)

    def test_no_updates_hints_to_write_start(self):
        with patch('notifications.management.commands.fetch_chat_ids.get_updates', return_value=[]):
            out, _ = self._run()

        self.assertIn('/start', out)

    def test_telegram_error_is_reported(self):
        with patch('notifications.management.commands.fetch_chat_ids.get_updates',
                   side_effect=TelegramError('нет токена')):
            _, err = self._run()

        self.assertIn('нет токена', err)
