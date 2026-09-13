from rest_framework import serializers

from .models import Habit
from .validators import (
    DurationValidator,
    PeriodicityValidator,
    PleasantHabitValidator,
    RelatedHabitIsPleasantValidator,
    RewardOrRelatedHabitValidator,
)


class HabitSerializer(serializers.ModelSerializer):
    """Привычка целиком — для CRUD владельца."""

    sentence = serializers.SerializerMethodField(
        read_only=True,
        help_text='Привычка одной фразой, как в книге.',
    )

    class Meta:
        model = Habit
        fields = (
            'id',
            'action',
            'time',
            'place',
            'sentence',
            'is_pleasant',
            'related_habit',
            'reward',
            'periodicity',
            'duration',
            'is_public',
            'user',
            'created_at',
        )
        read_only_fields = ('user', 'created_at')
        validators = [
            RewardOrRelatedHabitValidator(),
            DurationValidator(),
            RelatedHabitIsPleasantValidator(),
            PleasantHabitValidator(),
            PeriodicityValidator(),
        ]

    def get_sentence(self, obj: Habit) -> str:
        return str(obj)

    def validate_related_habit(self, value):
        """Связанной может быть только своя привычка.

        Иначе через чужой id можно было бы узнать, что у другого
        пользователя есть привычка с таким номером.
        """
        request = self.context.get('request')
        if value and request and value.user != request.user:
            raise serializers.ValidationError('Связать можно только со своей привычкой.')
        return value


class PublicHabitSerializer(serializers.ModelSerializer):
    """Публичная витрина: чужие привычки только на просмотр.

    Владелец не раскрывается — показываем сам приём, а не автора.
    """

    sentence = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Habit
        fields = (
            'id',
            'action',
            'time',
            'place',
            'sentence',
            'is_pleasant',
            'reward',
            'periodicity',
            'duration',
        )

    def get_sentence(self, obj: Habit) -> str:
        return str(obj)
