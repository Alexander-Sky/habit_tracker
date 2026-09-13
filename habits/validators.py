"""Валидаторы привычек.

Правила взяты из книги «Атомные привычки»: привычка должна быть короткой,
а награда — либо приятной привычкой, либо чем-то ещё, но не двумя сразу.

Все валидаторы работают на уровне сериализатора и получают словарь полей,
поэтому корректно отрабатывают и при частичном обновлении (PATCH):
недостающие поля добираются из уже сохранённого объекта.
"""

from rest_framework.serializers import ValidationError

MAX_DURATION_SECONDS = 120
MAX_PERIODICITY_DAYS = 7
MIN_PERIODICITY_DAYS = 1


def _resolve(field: str, attrs: dict, instance):
    """Значение поля: из запроса, а если его там нет — из объекта в базе."""
    if field in attrs:
        return attrs[field]
    return getattr(instance, field, None)


class RewardOrRelatedHabitValidator:
    """Нельзя указать одновременно вознаграждение и связанную привычку."""

    requires_context = True

    def __call__(self, attrs, serializer=None):
        instance = getattr(serializer, 'instance', None)

        reward = _resolve('reward', attrs, instance)
        related_habit = _resolve('related_habit', attrs, instance)

        if reward and related_habit:
            raise ValidationError(
                'Выберите что-то одно: либо вознаграждение, либо связанную приятную привычку.'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class DurationValidator:
    """Привычка не должна занимать больше двух минут."""

    requires_context = True

    def __call__(self, attrs, serializer=None):
        instance = getattr(serializer, 'instance', None)
        duration = _resolve('duration', attrs, instance)

        if duration is not None and duration > MAX_DURATION_SECONDS:
            raise ValidationError(
                f'Время выполнения не должно превышать {MAX_DURATION_SECONDS} секунд, '
                f'сейчас указано {duration}.'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class RelatedHabitIsPleasantValidator:
    """В связанные попадают только приятные привычки."""

    requires_context = True

    def __call__(self, attrs, serializer=None):
        instance = getattr(serializer, 'instance', None)
        related_habit = _resolve('related_habit', attrs, instance)

        if related_habit and not related_habit.is_pleasant:
            raise ValidationError(
                'Связанной может быть только приятная привычка — '
                f'у привычки «{related_habit.action}» не стоит признак приятной.'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class PleasantHabitValidator:
    """У приятной привычки не может быть ни награды, ни связанной привычки."""

    requires_context = True

    def __call__(self, attrs, serializer=None):
        instance = getattr(serializer, 'instance', None)

        is_pleasant = _resolve('is_pleasant', attrs, instance)
        if not is_pleasant:
            return

        if _resolve('reward', attrs, instance):
            raise ValidationError(
                'Приятная привычка сама является наградой, вознаграждение ей не нужно.'
            )

        if _resolve('related_habit', attrs, instance):
            raise ValidationError(
                'У приятной привычки не может быть связанной привычки.'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class PeriodicityValidator:
    """Привычку нужно выполнять хотя бы раз в неделю, но не чаще раза в день."""

    requires_context = True

    def __call__(self, attrs, serializer=None):
        instance = getattr(serializer, 'instance', None)
        periodicity = _resolve('periodicity', attrs, instance)

        if periodicity is None:
            return

        if periodicity < MIN_PERIODICITY_DAYS:
            raise ValidationError(
                f'Периодичность не может быть меньше {MIN_PERIODICITY_DAYS} дня.'
            )

        if periodicity > MAX_PERIODICITY_DAYS:
            raise ValidationError(
                f'Нельзя выполнять привычку реже, чем раз в {MAX_PERIODICITY_DAYS} дней — '
                f'сейчас указано раз в {periodicity}.'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)
