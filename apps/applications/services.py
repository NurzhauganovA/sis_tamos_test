from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .models import Application, ApplicationStatusHistory, ServiceProvider
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationStatusUpdateSerializer,
    ApplicationCommentCreateSerializer
)
from apps.user.models import UserRole, ParentMS
from ..contract.models import StudentMS


class ApplicationService:
    """Сервис для работы с заявками"""

    @staticmethod
    def get_applications_for_user(user, filters=None):
        """Получить заявки для конкретного пользователя с учетом его роли"""

        try:
            parent_role = UserRole.objects.get(role_name='Родитель')
            admin_roles = UserRole.objects.filter(
                role_name__in=['Администратор', 'Суперадмин']
            )
        except UserRole.DoesNotExist:
            return Application.objects.none()

        queryset = Application.objects.select_related(
            'applicant', 'application_type', 'assigned_to', 'campus', 'subdivision1', 'subdivision2'
        ).prefetch_related('files', 'comments')

        # Фильтрация по роли пользователя
        if user.role == parent_role:
            # Родители видят только свои заявки
            queryset = queryset.filter(applicant=user)
        elif user.role in admin_roles:
            # Администраторы видят все заявки
            pass
        else:
            # Поставщики услуг видят заявки по своим услугам
            user_services = ServiceProvider.objects.filter(
                account=user,
                is_active=True
            )
            if user_services.exists():
                service_provider = user_services.first()
                service_type_ids = user_services.values_list('application_types__id', flat=True)
                queryset = queryset.filter(application_type_id__in=service_type_ids)

                if service_provider.campus:
                    queryset = queryset.filter(campus=service_provider.campus)
            else:
                return Application.objects.none()

        # Применяем дополнительные фильтры
        if filters:
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])

            if filters.get('application_type'):
                queryset = queryset.filter(application_type=filters['application_type'])

            if filters.get('student_id'):
                queryset = queryset.filter(student_id=filters['student_id'])

            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])

            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])

            if filters.get('search'):
                search_query = filters['search']
                queryset = queryset.filter(
                    Q(subject__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(student__full_name__icontains=search_query)
                )

        return queryset.order_by('-created_at')

    @staticmethod
    def get_user_students(user):
        """Получить список студентов пользователя"""
        login_format = str(user.login).split('+7')[1] if user.login.startswith('+7') else user.login

        try:
            parent_ms = ParentMS.objects.using('ms_sql').filter(phone=login_format).first()
            if not parent_ms:
                return []

            students_ms = StudentMS.objects.using('ms_sql').filter(parent_id=parent_ms.id)
            return [
                {
                    'id': student.id,
                    'full_name': student.full_name,
                    'iin': getattr(student, 'iin', None)
                }
                for student in students_ms
            ]
        except Exception:
            return []

    @staticmethod
    def get_all_campuses():
        # get list of all distinct campuses from Application model
        result = []
        campuses = Application.objects.values_list('campus', flat=True).distinct()
        for campus in campuses:
            if campus and campus not in result:
                result.append(campus)

        return {
            'campuses': result
        }


class ApplicationCreateService:
    """Сервис для создания заявок"""

    def create_application(self, request):
        """Создать новую заявку"""
        serializer = ApplicationCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            application = serializer.save()

            # Возвращаем детальную информацию о созданной заявке
            detail_serializer = ApplicationDetailSerializer(application)
            return Response(
                detail_serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ApplicationStatusService:
    """Сервис для управления статусами заявок"""

    def update_status(self, application, request):
        """Обновить статус заявки"""
        serializer = ApplicationStatusUpdateSerializer(
            application,
            data=request.data,
            context={'request': request},
            partial=True
        )

        if serializer.is_valid():
            updated_application = serializer.save()

            detail_serializer = ApplicationDetailSerializer(updated_application)
            return Response(detail_serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def accept_application(self, application, request):
        """Принять заявку в работу"""
        if application.status != 'new':
            return Response(
                {'error': 'Можно принять только новые заявки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self.update_status(
            application,
            type('Request', (), {
                'data': {'status': 'in_progress'},
                'user': request.user
            })()
        )

    def reject_application(self, application, request):
        """Отклонить заявку"""
        if application.status in ['completed', 'rejected']:
            return Response(
                {'error': 'Нельзя отклонить завершенную или уже отклоненную заявку'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Причина отклонения обязательна'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self.update_status(
            application,
            type('Request', (), {
                'data': {'status': 'rejected', 'reason': reason},
                'user': request.user
            })()
        )

    def complete_application(self, application, request):
        """Завершить заявку"""
        if application.status != 'in_progress':
            return Response(
                {'error': 'Можно завершить только заявки в работе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self.update_status(
            application,
            type('Request', (), {
                'data': {'status': 'completed'},
                'user': request.user
            })()
        )


class ApplicationCommentService:
    """Сервис для работы с комментариями"""

    def add_comment(self, application, request):
        """Добавить комментарий к заявке"""
        serializer = ApplicationCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'application': application}
        )

        if serializer.is_valid():
            comment = serializer.save()
            return Response(
                {'id': comment.id, 'message': 'Комментарий добавлен'},
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ApplicationStatisticsService:
    """Сервис для получения статистики по заявкам"""

    @staticmethod
    def get_statistics_for_user(user):
        """Получить статистику заявок для пользователя"""
        queryset = ApplicationService.get_applications_for_user(user)

        total = queryset.count()
        new_count = queryset.filter(status='new').count()
        in_progress_count = queryset.filter(status='in_progress').count()
        completed_count = queryset.filter(status='completed').count()
        rejected_count = queryset.filter(status='rejected').count()

        return {
            'total': total,
            'new': new_count,
            'in_progress': in_progress_count,
            'completed': completed_count,
            'rejected': rejected_count
        }