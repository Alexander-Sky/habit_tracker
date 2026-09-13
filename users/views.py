from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .serializers import UserRegisterSerializer, UserSerializer


@extend_schema(
    tags=['auth'],
    summary='Регистрация',
    description=(
        'Создаёт пользователя. Доступна без токена — вместе с получением токенов '
        'это единственные открытые эндпоинты.\n\n'
        'Пароль проходит валидаторы Django и сохраняется хешем, в ответе не возвращается.'
    ),
    responses={
        201: UserRegisterSerializer,
        400: OpenApiResponse(description='Email занят или пароль слишком простой'),
    },
)
class UserRegisterAPIView(generics.CreateAPIView):
    """Регистрация нового пользователя."""

    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny,)


@extend_schema(
    tags=['users'],
    summary='Мой профиль',
    description=(
        'Данные текущего пользователя. `telegram_chat_id` заполняется после того, '
        'как человек напишет боту команду /start — без него напоминания слать некуда.'
    ),
)
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """Просмотр и редактирование своего профиля."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
