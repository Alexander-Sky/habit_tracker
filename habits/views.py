from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Habit
from .paginators import HabitPaginator
from .permissions import IsOwner
from .serializers import HabitSerializer, PublicHabitSerializer


@extend_schema(tags=['habits'])
@extend_schema_view(
    list=extend_schema(
        summary='Мои привычки',
        description=(
            'Список привычек текущего пользователя. Чужие сюда не попадают.\n\n'
            'Постранично, по пять штук. Размер страницы меняется параметром '
            '`limit`, смещение — `offset`.'
        ),
    ),
    create=extend_schema(
        summary='Создать привычку',
        description=(
            'Владельцем становится автор запроса, передавать его не нужно.\n\n'
            'Проверяется пять правил: нельзя указать награду и связанную привычку '
            'одновременно, выполнение не длиннее 120 секунд, связанной может быть '
            'только приятная привычка, у приятной нет ни награды, ни связанной, '
            'периодичность от 1 до 7 дней.'
        ),
        responses={
            201: HabitSerializer,
            400: OpenApiResponse(description='Нарушено одно из правил'),
        },
        examples=[
            OpenApiExample(
                'Полезная привычка с приятной в награду',
                value={
                    'action': 'гулять вокруг квартала',
                    'time': '19:30:00',
                    'place': 'район у дома',
                    'related_habit': 2,
                    'periodicity': 1,
                    'duration': 120,
                },
                request_only=True,
            ),
            OpenApiExample(
                'Приятная привычка',
                value={
                    'action': 'принять ванну с пеной',
                    'time': '21:00:00',
                    'place': 'дома',
                    'is_pleasant': True,
                    'duration': 120,
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(summary='Одна привычка', description='Доступна только владельцу.'),
    update=extend_schema(summary='Заменить привычку', description='Доступно только владельцу.'),
    partial_update=extend_schema(summary='Изменить привычку', description='Доступно только владельцу.'),
    destroy=extend_schema(summary='Удалить привычку', description='Доступно только владельцу.'),
)
class HabitViewSet(viewsets.ModelViewSet):
    """CRUD привычек текущего пользователя."""

    serializer_class = HabitSerializer
    permission_classes = (IsAuthenticated, IsOwner)
    pagination_class = HabitPaginator

    def get_queryset(self):
        """Пользователь работает только со своими привычками.

        Фильтрация на уровне выборки, а не только прав: чужая привычка
        просто не существует для этого пользователя и вернёт 404.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Habit.objects.none()
        return Habit.objects.filter(user=self.request.user).select_related('related_habit')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(
    tags=['public'],
    summary='Публичные привычки',
    description=(
        'Витрина привычек, которые пользователи открыли для всех. '
        'Только чтение: редактировать и удалять чужое нельзя.\n\n'
        'Автор не раскрывается — показывается сам приём.'
    ),
)
class PublicHabitListAPIView(generics.ListAPIView):
    """Список публичных привычек — доступен всем авторизованным."""

    queryset = Habit.objects.filter(is_public=True)
    serializer_class = PublicHabitSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = HabitPaginator
