"""Фоновая рассылка напоминаний о привычках."""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from habits.models import Habit

from .services import send_telegram_message

logger = logging.getLogger(__name__)


def build_reminder_text(habit: Habit) -> str:
    """Текст напоминания.

    Кроме самой формулы из книги добавляем награду — она и есть то,
    ради чего привычка выполняется.
    """
    lines = [f'Пора: {habit.action}', f'Место: {habit.place}']

    if habit.related_habit:
        lines.append(f'Награда: {habit.related_habit.action}')
    elif habit.reward:
        lines.append(f'Награда: {habit.reward}')

    lines.append(f'Займёт около {habit.duration} секунд.')
    return '\n'.join(lines)


def is_due(habit: Habit, now: datetime) -> bool:
    """Пора ли напоминать с учётом периодичности.

    Привычка с периодичностью 3 напоминает раз в три дня, а не каждый день
    в одно и то же время. Первый раз — всегда.
    """
    if habit.last_reminded_at is None:
        return True

    return now - habit.last_reminded_at >= timedelta(days=habit.periodicity)


@shared_task
def send_habit_reminders() -> int:
    """Рассылает напоминания о привычках, время которых подошло.

    Запускается celery-beat раз в минуту. Возвращает количество
    отправленных сообщений — попадает в лог воркера.

    Окно REMINDER_WINDOW_MINUTES нужно на случай, если воркер был занят
    или лежал: напоминание уйдёт с задержкой, а не пропадёт совсем.
    """
    now = timezone.localtime()

    # У нижней границы окна микросекунды отбрасываем: время привычки ровное
    # (05:02:00), а граница приходит с хвостом (05:02:00.005), и ровно
    # пограничная минута отсеивалась бы. Верхнюю границу не трогаем —
    # иначе потеряется привычка, заведённая с долями секунды
    window_start = (
        now - timedelta(minutes=settings.REMINDER_WINDOW_MINUTES)
    ).replace(microsecond=0).time()
    current_time = now.time()

    if window_start <= current_time:
        window = Q(time__gte=window_start, time__lte=current_time)
    else:
        # Окно перешагнуло полночь: 23:57 — 00:02 это два отрезка,
        # обычное «между» здесь дало бы пустую выборку
        window = Q(time__gte=window_start) | Q(time__lte=current_time)

    habits = (
        Habit.objects
        .filter(window, user__is_active=True)
        .exclude(user__telegram_chat_id__isnull=True)
        .exclude(user__telegram_chat_id='')
        .select_related('user', 'related_habit')
    )

    sent = 0
    for habit in habits:
        if not is_due(habit, now):
            continue

        if send_telegram_message(habit.user.telegram_chat_id, build_reminder_text(habit)):
            # Отметку ставим только при успешной отправке: если телеграм
            # был недоступен, следующий запуск попробует ещё раз
            habit.last_reminded_at = now
            habit.save(update_fields=['last_reminded_at'])
            sent += 1

    if sent:
        logger.info('Отправлено напоминаний: %s', sent)

    return sent
