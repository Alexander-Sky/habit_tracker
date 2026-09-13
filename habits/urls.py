from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HabitViewSet, PublicHabitListAPIView

app_name = 'habits'

router = DefaultRouter()
router.register(r'habits', HabitViewSet, basename='habit')

urlpatterns = [
    # Публичная витрина объявлена до роутера: иначе `habits/public/`
    # будет разобрано как запрос привычки с id = "public"
    path('habits/public/', PublicHabitListAPIView.as_view(), name='habit-public'),
    path('', include(router.urls)),
]
