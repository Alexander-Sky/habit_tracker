from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import UserProfileAPIView, UserRegisterAPIView

app_name = 'users'

LoginView = extend_schema(
    tags=['auth'],
    summary='Получить пару токенов',
    description='Принимает email и пароль, возвращает access и refresh. Доступен без токена.',
)(TokenObtainPairView)

RefreshView = extend_schema(
    tags=['auth'],
    summary='Обновить access-токен',
    description='Принимает refresh, возвращает новый access. Доступен без токена.',
)(TokenRefreshView)

urlpatterns = [
    path('register/', UserRegisterAPIView.as_view(), name='register'),
    path('login/', LoginView.as_view(permission_classes=(AllowAny,)), name='login'),
    path('token/refresh/', RefreshView.as_view(permission_classes=(AllowAny,)), name='token-refresh'),
    path('profile/', UserProfileAPIView.as_view(), name='profile'),
]
