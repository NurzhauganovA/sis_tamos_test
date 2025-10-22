from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import Application, ApplicationType, ServiceProvider, SchoolApplication
from .serializers import (
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
    ApplicationTypeSerializer,
    ServiceProviderSerializer,
    StudentSimpleSerializer, ApplicationTypeCreateSerializer, ApplicationTypeUpdateSerializer,
    ServiceProviderCreateSerializer, ServiceProviderUpdateSerializer, AccountCreateServiceProviderSerializer,
    AccountServiceProviderSerializer, ApplicationCampusSerializer, CampusListSerializer, Subdivision1ListSerializer,
    Subdivision2ListSerializer, AccountUpdateServiceProviderSerializer
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
from ..school.models import SchoolMS
from ..user.models import ParentMS, User, UserRole, UserInfo


class ApplicationPagination(PageNumberPagination):
    """Пагинация для заявок"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с заявками"""

    permission_classes = [IsAuthenticated]
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
    )
    def accept(self, request, pk=None):
        """Принять заявку в работу"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.accept_application(application, request)

    @action(
        detail=True,
        methods=['post'],
    )
    def reject(self, request, pk=None):
        """Отклонить заявку"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.reject_application(application, request)

    @action(
        detail=True,
        methods=['post'],
    )
    def complete(self, request, pk=None):
        """Завершить заявку"""
        application = self.get_object()
        service = ApplicationStatusService()
        return service.complete_application(application, request)

    @action(
        detail=True,
        methods=['post'],
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
    """ViewSet для управления аккаунтами поставщиков услуг"""

    serializer_class = AccountCreateServiceProviderSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    http_method_names = ['get', 'post', 'delete', 'patch']

    def get_queryset(self):
        """Получить всех пользователей, связанных с service_provider"""
        from apps.user.models import UserInfo
        # Получаем ID пользователей, у которых есть связь с service_provider
        user_ids = UserInfo.objects.filter(
            service_provider_id__isnull=False
        ).values_list('user_id', flat=True)

        return User.objects.filter(id__in=user_ids)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AccountServiceProviderSerializer
        if self.action in ['partial_update']:
            return AccountUpdateServiceProviderSerializer
        return AccountCreateServiceProviderSerializer

    def list(self, request, *args, **kwargs):
        """Получить список всех аккаунтов с информацией о service_provider"""
        from apps.user.models import UserInfo

        queryset = self.get_queryset()

        # Формируем данные с информацией о service_provider
        result = []
        for user in queryset:
            try:
                user_info = UserInfo.objects.get(user=user)
                service_provider = ServiceProvider.objects.get(id=user_info.service_provider_id)

                data = {
                    'id': user.id,
                    'fio': user.fio,
                    'login': user.login,
                    'role': user.role.role_name if user.role else None,
                    'is_active': user.is_active,
                    'service_provider': {
                        'id': service_provider.id,
                        'name': service_provider.name,
                        'bin_or_iin': service_provider.bin_or_iin,
                        'service_type': service_provider.service_type,
                        'description': service_provider.description,
                        'responsible_full_name': service_provider.responsible_full_name,
                        'responsible_phone': service_provider.responsible_phone,
                        'responsible_email': service_provider.responsible_email,
                        'campus': service_provider.campus,
                        'subdivision1': service_provider.subdivision1,
                        'subdivision2': service_provider.subdivision2,
                        'is_active': service_provider.is_active
                    }
                }
                result.append(data)
            except (UserInfo.DoesNotExist, ServiceProvider.DoesNotExist):
                continue

        serializer = AccountServiceProviderSerializer(result, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Получить конкретный аккаунт с информацией о service_provider"""
        from apps.user.models import UserInfo

        user = self.get_object()

        try:
            user_info = UserInfo.objects.get(user=user)
            service_provider = ServiceProvider.objects.get(id=user_info.service_provider_id)

            data = {
                'id': user.id,
                'fio': user.fio,
                'login': user.login,
                'role': user.role.role_name if user.role else None,
                'is_active': user.is_active,
                'service_provider': {
                    'id': service_provider.id,
                    'name': service_provider.name,
                    'bin_or_iin': service_provider.bin_or_iin,
                    'service_type': service_provider.service_type,
                    'description': service_provider.description,
                    'responsible_full_name': service_provider.responsible_full_name,
                    'responsible_phone': service_provider.responsible_phone,
                    'responsible_email': service_provider.responsible_email,
                    'campus': service_provider.campus,
                    'subdivision1': service_provider.subdivision1,
                    'subdivision2': service_provider.subdivision2,
                    'is_active': service_provider.is_active
                }
            }

            serializer = AccountServiceProviderSerializer(data)
            return Response(serializer.data)
        except (UserInfo.DoesNotExist, ServiceProvider.DoesNotExist):
            return Response(
                {'error': 'Service provider информация не найдена для данного пользователя'},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        """Создать аккаунт поставщика услуг"""
        from apps.user.models import UserInfo

        data = request.data

        # Проверка существования пользователя
        if User.objects.filter(login=data['login']).exists():
            return Response(
                {'error': 'Пользователь с таким логином уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка совпадения паролей
        if data['password'] != data['password2']:
            return Response(
                {'error': 'Пароли не совпадают'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка наличия service_type
        if 'service_type' not in data or not data['service_type']:
            return Response(
                {"error": "Тип услуги (service_type) обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка существования service_provider
        service_provider_id = data.get('service_provider_id')
        if not service_provider_id:
            return Response(
                {"error": "service_provider_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service_provider = ServiceProvider.objects.get(id=service_provider_id)
        except ServiceProvider.DoesNotExist:
            return Response(
                {"error": "Service provider с указанным ID не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Создание или получение роли
        service_type = data.get("service_type")
        user_role, created = UserRole.objects.get_or_create(role_name=service_type)

        # Создание пользователя
        provider = User.objects.create_user(
            login=data['login'],
            password=data['password'],
            is_active=True,
            fio=data['responsible_full_name'],
            role=user_role,
            is_work=False
        )
        provider.set_password(data['password'])
        provider.save()

        # Создание связи с service_provider
        user_info = UserInfo.objects.create(
            user=provider,
            service_provider_id=service_provider_id
        )

        # Формирование ответа
        response_data = {
            'id': provider.id,
            'fio': provider.fio,
            'login': provider.login,
            'role': provider.role.role_name,
            'is_active': provider.is_active,
            'service_provider': {
                'id': service_provider.id,
                'name': service_provider.name,
                'bin_or_iin': service_provider.bin_or_iin,
                'service_type': service_provider.service_type,
                'description': service_provider.description,
                'responsible_full_name': service_provider.responsible_full_name,
                'responsible_phone': service_provider.responsible_phone,
                'responsible_email': service_provider.responsible_email,
                'campus': service_provider.campus,
                'subdivision1': service_provider.subdivision1,
                'subdivision2': service_provider.subdivision2,
                'is_active': service_provider.is_active
            }
        }

        serializer = AccountServiceProviderSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()

        return Response({'detail': 'Пользователь стал неактивным'}, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        from apps.user.models import UserInfo
        from .models import ServiceProvider

        user = self.get_object()
        user_info = UserInfo.objects.filter(user=user).first()
        service_provider = None
        if user_info:
            service_provider = ServiceProvider.objects.filter(id=user_info.service_provider_id).first()

        serializer = AccountUpdateServiceProviderSerializer(
            instance={
                'service_provider_id': user_info.service_provider_id if user_info else None,
                'responsible_full_name': service_provider.responsible_full_name if service_provider else '',
                'service_type': service_provider.service_type if service_provider else '',
                'login': user.login,
                'is_active': user.is_active
            },
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        # Обновляем поля пользователя
        if 'service_provider_id' in validated:
            user_info.service_provider_id = validated['service_provider_id']
            user_info.save()

        if 'login' in validated:
            if User.objects.filter(login=validated['login']).exists() and user.login != validated['login']:
                return Response({'detail': "Пользователь с таким номером уже существует!"}, status=status.HTTP_400_BAD_REQUEST)
            user.login = validated['login']
            user.save()

        if 'service_type' in validated:
            user_role = UserRole.objects.filter(role_name=validated['service_type']).first()
            if not user_role:
                user_role = UserRole.objects.create(role_name=validated['service_type'])
            user.role = user_role
            user.save()

        if 'is_active' in validated:
            user.is_active = validated['is_active']
            user.save()

        # Обновляем поля сервис-провайдера
        if service_provider:
            if 'responsible_full_name' in validated:
                service_provider.responsible_full_name = validated['responsible_full_name']
                user.fio = validated['responsible_full_name']
            service_provider.save()
            user.save()

        # Возвращаем обновлённые данные
        response_serializer = AccountServiceProviderSerializer({
            'id': user.id,
            'fio': user.fio,
            'login': user.login,
            'role': user.role.role_name if user.role else None,
            'is_active': user.is_active,
            'service_provider': service_provider
        })
        return Response(response_serializer.data)




class SchoolDataViewSet(viewsets.ViewSet):
    """ViewSet для получения данных о школах из MS SQL"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='campuses')
    def get_campuses(self, request):
        """
        Получить список уникальных кампусов (sSchool_name)
        GET /api/v1/school/data/campuses/
        """
        campuses = SchoolApplication.objects.values_list(
            'sSchool_name', flat=True
        ).distinct().order_by('sSchool_name')

        # Убираем пустые значения и преобразуем в список
        unique_campuses = [campus for campus in campuses if campus]

        serializer = CampusListSerializer({'campuses': unique_campuses})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='subdivisions1')
    def get_subdivisions1(self, request):
        """
        Получить список уникальных subdivision1 (sSchool_direct) для выбранного campus
        GET /api/v1/school/data/subdivisions1/?campus=<campus_name>
        """
        campus = request.query_params.get('campus')

        if not campus:
            return Response(
                {'error': 'Параметр campus обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subdivisions = SchoolApplication.objects.filter(
            sSchool_name=campus
        ).values_list('sSchool_direct', flat=True).distinct().order_by('sSchool_direct')

        # Убираем пустые значения и преобразуем в список
        unique_subdivisions = [sub for sub in subdivisions if sub]

        serializer = Subdivision1ListSerializer({'subdivisions': unique_subdivisions})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='subdivisions2')
    def get_subdivisions2(self, request):
        """
        Получить список уникальных subdivision2 (sSchool_language) для выбранного campus и subdivision1
        GET /api/v1/school/data/subdivisions2/?campus=<campus_name>&subdivision1=<subdivision1_name>
        """
        campus = request.query_params.get('campus')
        subdivision1 = request.query_params.get('subdivision1')

        if not campus:
            return Response(
                {'error': 'Параметр campus обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not subdivision1:
            return Response(
                {'error': 'Параметр subdivision1 обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subdivisions = SchoolApplication.objects.filter(
            sSchool_name=campus,
            sSchool_direct=subdivision1
        ).values_list('sSchool_language', flat=True).distinct().order_by('sSchool_language')

        # Убираем пустые значения и преобразуем в список
        unique_subdivisions = [sub for sub in subdivisions if sub]

        serializer = Subdivision2ListSerializer({'subdivisions': unique_subdivisions})
        return Response(serializer.data)
