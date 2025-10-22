from rest_framework import permissions
from .models import Application, ServiceProvider
from apps.user.models import UserRole


class IsParent(permissions.BasePermission):
    """Разрешение для родителей"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            parent_role = UserRole.objects.get(role_name='Родитель')
            return request.user.role == parent_role
        except UserRole.DoesNotExist:
            return False


class IsServiceProvider(permissions.BasePermission):
    """Разрешение для поставщиков услуг"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.role.role_name != "Поставщик":
            return False

        # Проверяем, является ли пользователь ответственным за какую-либо услугу
        return ServiceProvider.objects.filter(
            responsible_person=request.user,
            is_active=True
        ).exists()


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Разрешение для администраторов"""

    def has_permission(self, request, view):
        return request.user.role.role_name == 'Суперадмин' or request.user.role.role_name == 'Администратор'


class ApplicationPermission(permissions.BasePermission):
    """Основное разрешение для работы с заявками"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Все аутентифицированные пользователи могут просматривать список
        if view.action in ['list', 'retrieve']:
            return True

        # Только родители могут создавать заявки
        if view.action == 'create':
            return IsParent().has_permission(request, view) or IsAdminOrSuperAdmin().has_permission(request, view)

        # Обновление и удаление для родителей и сервис-провайдеров
        if view.action in ['update', 'partial_update', 'destroy']:
            return (IsParent().has_permission(request, view) or
                    IsServiceProvider().has_permission(request, view) or
                    IsAdminOrSuperAdmin().has_permission(request, view))

        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Администраторы имеют полный доступ
        if IsAdminOrSuperAdmin().has_permission(request, view):
            return True

        # Родители могут работать только со своими заявками
        if IsParent().has_permission(request, view):
            if view.action in ['retrieve', 'update', 'partial_update']:
                return obj.applicant == request.user
            if view.action == 'destroy':
                # Родители могут удалять только новые заявки
                return obj.applicant == request.user and obj.status == 'new'

        # Поставщики услуг могут работать с заявками по своим услугам
        if IsServiceProvider().has_permission(request, view):
            user_services = ServiceProvider.objects.filter(
                responsible_person=request.user,
                is_active=True
            )
            service_types = user_services.values_list('application_types', flat=True)
            return obj.application_type_id in service_types

        return False


class ApplicationStatusPermission(permissions.BasePermission):
    """Разрешение для изменения статуса заявки"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return (IsServiceProvider().has_permission(request, view) or
                IsAdminOrSuperAdmin().has_permission(request, view))

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Администраторы могут изменять любые статусы
        if IsAdminOrSuperAdmin().has_permission(request, view):
            return True

        # Поставщики услуг могут изменять статусы своих заявок
        if IsServiceProvider().has_permission(request, view):
            user_services = ServiceProvider.objects.filter(
                responsible_person=request.user,
                is_active=True
            )
            service_types = user_services.values_list('application_types', flat=True)
            return obj.application_type_id in service_types

        return False


class ApplicationCommentPermission(permissions.BasePermission):
    """Разрешение для комментариев к заявке"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True  # Все аутентифицированные пользователи могут комментировать

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        application = obj if isinstance(obj, Application) else obj.application

        # Администраторы имеют полный доступ
        if IsAdminOrSuperAdmin().has_permission(request, view):
            return True

        # Заявители могут комментировать свои заявки
        if application.applicant == request.user:
            return True

        # Поставщики услуг могут комментировать заявки по своим услугам
        if IsServiceProvider().has_permission(request, view):
            user_services = ServiceProvider.objects.filter(
                responsible_person=request.user,
                is_active=True
            )
            service_types = user_services.values_list('application_types', flat=True)
            return application.application_type_id in service_types

        return False