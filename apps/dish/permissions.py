from rest_framework import permissions
from apps.user.models import UserRole


class IsNutritionController(permissions.BasePermission):
    """ Проверка на роль `Питание` """

    role = UserRole.objects.get(role_name="Питание").id

    def has_permission(self, request, view):
        return bool(request.user.role_id_id == self.role and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user.role_id_id == self.role and request.user.is_authenticated)
