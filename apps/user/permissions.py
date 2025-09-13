from rest_framework import permissions
from apps.user.models import UserRole


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user_role_id = UserRole.objects.get(role_name='Администратор')

        if request.user.is_authenticated:
            return request.user.role == user_role_id
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user_role_id = UserRole.objects.get(role_name='Администратор')

        if request.user.is_authenticated:
            return request.user.role == user_role_id
        else:
            return False


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user_role_id = UserRole.objects.get(role_name='Суперадмин')

        if request.user.is_authenticated:
            return request.user.role == user_role_id
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user_role_id = UserRole.objects.get(role_name='Суперадмин')

        if request.user.is_authenticated:
            return request.user.role == user_role_id
        else:
            return False
