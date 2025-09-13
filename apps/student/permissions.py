from rest_framework import permissions
from apps.student.models import Student
from apps.user.models import UserRole


class StudentPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action == 'list' or view.action == 'update':
            parent_user = request.user
            student_id = view.kwargs.get('pk')
            student = Student.objects.filter(parent=parent_user, id=student_id).exists()
            return student
        elif view.action == 'create':
            return True
        elif view.action in ['retrieve', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if view.action == 'retrieve':
            return obj == request.user or request.user.is_admin
        elif view.action in ['update', 'partial_update']:
            return obj == request.user or request.user.is_admin
        elif view.action == 'destroy':
            return request.user.is_admin
        else:
            return False


class IsParentRole(permissions.BasePermission):
    def has_permission(self, request, view):
        parent_role_id = UserRole.objects.filter(role_name='Родитель').first()

        if request.user.is_authenticated:
            return request.user.role == parent_role_id
        else:
            return False

    def has_object_permission(self, request, view, obj):
        parent_role_id = UserRole.objects.filter(role_name='Родитель').first()

        if request.user.is_authenticated:
            return request.user.role == parent_role_id
        else:
            return False
