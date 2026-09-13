from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Доступ только к своим привычкам."""

    message = 'Это чужая привычка.'

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
