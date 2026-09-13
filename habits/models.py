from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import (
    MAX_DURATION_SECONDS,
    MAX_PERIODICITY_DAYS,
    MIN_PERIODICITY_DAYS,
)

NULLABLE = {'blank': True, 'null': True}


class Habit(models.Model):
    """Привычка.

    Формула из книги: «я буду [ДЕЙСТВИЕ] в [ВРЕМЯ] в [МЕСТО]».

    Привычки бывают двух видов. Полезная — то, что человек хочет делать,
    за неё полагается награда: либо приятная привычка в поле related_habit,
    либо что-то другое в поле reward. Приятная — сама по себе награда,
    у неё ни того, ни другого быть не должно.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits',
        verbose_name='Пользователь',
    )
    place = models.CharField(
        max_length=255,
        verbose_name='Место',
        help_text='Где выполняется привычка',
    )
    time = models.TimeField(
        verbose_name='Время',
        help_text='Во сколько напоминать',
    )
    action = models.CharField(
        max_length=255,
        verbose_name='Действие',
        help_text='Что именно нужно сделать',
    )
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name='Признак приятной привычки',
        help_text='Приятная привычка служит наградой за полезную',
    )
    related_habit = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='rewarded_habits',
        verbose_name='Связанная привычка',
        help_text='Приятная привычка, которой вы себя награждаете',
        **NULLABLE,
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(MIN_PERIODICITY_DAYS),
            MaxValueValidator(MAX_PERIODICITY_DAYS),
        ],
        verbose_name='Периодичность в днях',
        help_text='От 1 до 7 дней',
    )
    reward = models.CharField(
        max_length=255,
        verbose_name='Вознаграждение',
        help_text='Чем вы себя наградите, если не выбрана приятная привычка',
        **NULLABLE,
    )
    duration = models.PositiveSmallIntegerField(
        default=60,
        validators=[MaxValueValidator(MAX_DURATION_SECONDS)],
        verbose_name='Время на выполнение в секундах',
        help_text='Не больше 120 секунд',
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name='Признак публичности',
        help_text='Публичные привычки видны всем пользователям',
    )
    last_reminded_at = models.DateTimeField(
        verbose_name='Последнее напоминание',
        help_text='Служебное поле: по нему считается, пора ли напоминать снова',
        **NULLABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
        ordering = ('time', 'id')

    def __str__(self):
        return f'Я буду {self.action} в {self.time:%H:%M} в {self.place}'
