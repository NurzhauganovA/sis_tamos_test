from rest_framework import permissions
from .models import Application, ServiceProvider
from apps.user.models import UserRole, UserInfo


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

        try:
            user_info = UserInfo.objects.get(user=request.user)
            if user_info.service_provider_id:
                return ServiceProvider.objects.filter(
                    id=user_info.service_provider_id,
                    is_active=True
                ).exists()
        except UserInfo.DoesNotExist:
            pass

        return False


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Разрешение для администраторов"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not request.user.role:
            return False

        return request.user.role.role_name in ['Суперадмин', 'Администратор']


class ApplicationPermission(permissions.BasePermission):
    """Основное разрешение для работы с заявками"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Просмотр списка и деталей доступен всем аутентифицированным
        if view.action in ['list', 'retrieve']:
            return True

        # Создавать заявки могут: Родитель, Администратор, Суперадмин
        if view.action == 'create':
            return (IsParent().has_permission(request, view) or
                    IsAdminOrSuperAdmin().has_permission(request, view))

        # Обновление и удаление
        if view.action in ['update', 'partial_update', 'destroy']:
            return (IsParent().has_permission(request, view) or
                    IsServiceProvider().has_permission(request, view) or
                    IsAdminOrSuperAdmin().has_permission(request, view))

        # Действия со статусами (accept, reject, complete)
        if view.action in ['accept', 'reject', 'complete']:
            return (IsServiceProvider().has_permission(request, view) or
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
            if view.action == 'retrieve':
                return obj.applicant == request.user
            if view.action in ['update', 'partial_update']:
                # Родители могут редактировать только новые заявки
                return obj.applicant == request.user and obj.status == 'new'
            if view.action == 'destroy':
                # Родители могут удалять только новые заявки
                return obj.applicant == request.user and obj.status == 'new'

        # Поставщики услуг могут работать с заявками по своему типу услуг
        if IsServiceProvider().has_permission(request, view):
            try:
                user_info = UserInfo.objects.get(user=request.user)
                service_provider = ServiceProvider.objects.get(
                    id=user_info.service_provider_id,
                    is_active=True
                )

                # Проверяем совпадение service_type и application_type
                application_type = obj.application_type

                # Поставщик имеет доступ, если service_type совпадает с названием типа заявки
                return service_provider == application_type.service_provider

            except (UserInfo.DoesNotExist, ServiceProvider.DoesNotExist):
                return False

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
            try:
                user_info = UserInfo.objects.get(user=request.user)
                service_provider = ServiceProvider.objects.get(
                    id=user_info.service_provider_id,
                    is_active=True
                )

                # Проверяем совпадение service_type и application_type
                application_type = obj.application_type
                return service_provider == application_type.service_provider

            except (UserInfo.DoesNotExist, ServiceProvider.DoesNotExist):
                return False

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

        # Поставщики услуг могут комментировать заявки по своему типу
        if IsServiceProvider().has_permission(request, view):
            try:
                user_info = UserInfo.objects.get(user=request.user)
                service_provider = ServiceProvider.objects.get(
                    id=user_info.service_provider_id,
                    is_active=True
                )

                application_type = application.application_type
                return service_provider == application_type.service_provider

            except (UserInfo.DoesNotExist, ServiceProvider.DoesNotExist):
                return False

        return False