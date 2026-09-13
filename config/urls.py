from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny


def home(request):
    """Точка входа: подсказывает, где искать документацию."""
    return JsonResponse({
        'service': 'Трекер полезных привычек',
        'docs': {
            'swagger': '/api/docs/',
            'redoc': '/api/redoc/',
            'schema': '/api/schema/',
        },
    })


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),

    # Документация открыта без токена — фронтенд должен читать её до логина
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny]),
        name='redoc',
    ),

    path('api/', include('users.urls')),
    path('api/', include('habits.urls')),
]
