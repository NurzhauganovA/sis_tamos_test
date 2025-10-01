from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from .models import Application, ApplicationType, ServiceProvider
from .serializers import (
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
    ApplicationTypeSerializer,
    ServiceProviderSerializer,
    StudentSimpleSerializer, ApplicationTypeCreateSerializer, ApplicationTypeUpdateSerializer,
    ServiceProviderCreateSerializer, ServiceProviderUpdateSerializer, AccountCreateServiceProviderSerializer,
    AccountServiceProviderSerializer, ApplicationCampusSerializer
)
from .permissions import (
    ApplicationPermission,
    ApplicationStatusPermission,
    ApplicationCommentPermission,
    IsParent,
    IsServiceProvider,
    IsAdminOrSuperAdmin
)
from .services import (
    ApplicationService,
    ApplicationCreateService,
    ApplicationStatusService,
    ApplicationCommentService,
    ApplicationStatisticsService
)
from apps.student.models import Student
from ..contract.models import StudentMS
from ..user.models import ParentMS, User, UserRole


class ApplicationPagination(PageNumberPagination):
    """Пагинация для заявок"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с заявками"""

    permission_classes = [IsAuthenticated, ApplicationPermission]
    pagination_class = ApplicationPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'application_type']

    def get_queryset(self):
        """Получить queryset с учетом роли пользователя"""
        filters = {}

        # Фильтрация по параметрам запроса
        if self.request.query_params.get('status'):
            filters['status'] = self.request.query_params['status']

        if self.request.query_params.get('application_type'):
            filters['application_type'] = self.request.query_params['application_type']

        if self.request.query_params.get('student_id'):
            filters['student_id'] = self.request.query_params['student_id']

        if self.request.query_params.get('date_from'):
            filters['date_from'] = self.request.query_params['date_from']

        if self.request.query_params.get('date_to'):
            filters['date_to'] = self.request.query_params['date_to']

        if self.request.query_params.get('search'):
            filters['search'] = self.request.query_params['search']

        return ApplicationService.get_applications_for_user(
            self.request.user,
            filters=filters
        )

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return ApplicationListSerializer
        elif self.action == 'create':
            return ApplicationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ApplicationUpdateSerializer
        elif self.action in ['all_campuses']:
            return ApplicationCampusSerializer
        else:
            return ApplicationDetailSerializer

    def create(self, request, *args, **kwargs):
        """Создать новую заявку"""
        service = ApplicationCreateService()
        return service.create_application(request)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, ApplicationStatusPermission]
    )
    def accept(self, request, pk=None):
        """Принять заявку в работу"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.accept_application(application, request)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, ApplicationStatusPermission]
    )
    def reject(self, request, pk=None):
        """Отклонить заявку"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.reject_application(application, request)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, ApplicationStatusPermission]
    )
    def complete(self, request, pk=None):
        """Завершить заявку"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.complete_application(application, request)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, ApplicationCommentPermission]
    )
    def add_comment(self, request, pk=None):
        """Добавить комментарий к заявке"""
        application = self.get_object()
        service = ApplicationCommentService()
        return service.add_comment(application, request)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def statistics(self, request):
        """Получить статистику заявок"""
        stats = ApplicationStatisticsService.get_statistics_for_user(request.user)
        return Response(stats)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, IsParent]
    )
    def my_students(self, request):
        """Получить список студентов текущего пользователя"""
        students = Student.objects.filter(parent=request.user)
        serializer = StudentSimpleSerializer(students, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        serializer_class=ApplicationCampusSerializer
    )
    def all_campuses(self, request):
        """Получить все кампусы"""
        campuses = ApplicationService.get_all_campuses()
        print("CAMPUSES:", campuses)
        serializer = ApplicationCampusSerializer(campuses)
        return Response(serializer.data)


class ApplicationTypeViewSet(viewsets.ModelViewSet):
    """ViewSet для типов заявок"""

    queryset = ApplicationType.objects.filter(is_active=True)
    serializer_class = ApplicationTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ApplicationTypeCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ApplicationTypeUpdateSerializer
        return ApplicationTypeSerializer

    def get_queryset(self):
        """Фильтрация типов заявок по поставщику услуг"""
        queryset = super().get_queryset()

        service_provider = self.request.query_params.get('service_provider')
        if service_provider:
            queryset = queryset.filter(service_provider_id=service_provider)

        return queryset


class ServiceProviderViewSet(viewsets.ModelViewSet):
    """ViewSet для поставщиков услуг"""

    queryset = ServiceProvider.objects.filter(is_active=True)
    serializer_class = ServiceProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ServiceProviderCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ServiceProviderUpdateSerializer
        return ServiceProviderSerializer


class StudentApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для получения студентов родителя"""

    serializer_class = StudentSimpleSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin | IsParent]

    def get_queryset(self):
        """Получить только студентов текущего пользователя"""
        login_format = str(self.request.user.login).split('+7')[1]
        try:
            return StudentMS.objects.using('ms_sql').filter(parent_id=ParentMS.objects.using('ms_sql').filter(phone=login_format).first().id)
        except AttributeError:
            parent = ParentMS.objects.using('ms_sql').filter(phone=login_format).first()
            if parent:
                return StudentMS.objects.using('ms_sql').filter(parent_id=parent.id)
            else:
                return StudentMS.objects.using('ms_sql').none()


class AccountApplicationServiceProvider(viewsets.ModelViewSet):
    """APIView для получения поставщика услуг по аккаунту"""

    serializer_class = AccountCreateServiceProviderSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        """Получить поставщика услуг по аккаунту"""
        data = request.data

        if User.objects.filter(login=data['login']).exists():
            return Response({'error': 'Пользователь с таким логином уже существует'},
                            status=status.HTTP_400_BAD_REQUEST)

        if data['password'] != data['password2']:
            return Response({'error': 'Пароли не совпадают'}, status=status.HTTP_400_BAD_REQUEST)

        user_role = UserRole.objects.filter(role_name="Поставщик").first()
        if not user_role:
            UserRole.objects.create(role_name="Поставщик")

        provider = User.objects.create_user(
            login=data['login'],
            password=data['password'],
            is_active=True,
            fio=data['responsible_full_name'],
            role=UserRole.objects.get(role_name="Поставщик"),
            is_work=False
        )
        provider.set_password(data['password'])
        provider.save()

        serializer = AccountServiceProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

