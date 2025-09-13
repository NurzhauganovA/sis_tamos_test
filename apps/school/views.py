from decimal import Decimal

from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum, Count
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import School, Class, SchoolRequisites, SchoolMS
from .serializers import SchoolSerializer, CreateSchoolSerializer, SchoolRequisitesSerializer, SchoolUsersSerializer, \
    SchoolStudentsSerializer, SchoolClassesSerializer, SchoolParentsSerializer, SchoolTeachersSerializer
from .serializers.stud_class import ClassSerializer, UpdateStudentClasses, CreateClassSerializer

from .services import ClassCreateService
from ..contract.models import ContractMS, ContractFoodMS, ContractDriverMS, StudentMS
from ..contract.services import ContractService
from ..statement.models import Statement
from ..student.models import Student
from ..user.models import User, UserInfo
from ..user.permissions import IsAdmin, IsSuperAdmin


class SchoolView(ModelViewSet):
    """ API для школ """

    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    http_method_names = ['get', 'post', 'put']

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve' or self.action == 'update':
            return SchoolSerializer
        if self.action == 'create':
            return CreateSchoolSerializer

        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            schools = User.objects.filter(id=user.id).values_list('school', flat=True)
            return School.objects.filter(id__in=schools)
        elif IsSuperAdmin().has_permission(self.request, self):
            return School.objects.all()
        else:
            return School.objects.none()

    def create(self, request, *args, **kwargs):
        if School.objects.filter(sBin=request.data.get('sBin')).exists():
            return Response({'message': 'Школа с таким БИН уже существует!'}, status=status.HTTP_403_FORBIDDEN)

        try:
            school_serializer = self.get_serializer(data=request.data, partial=True)
            school_serializer.is_valid(raise_exception=True)
            school_serializer.save()
        except IntegrityError:
            last_school = School.objects.last()
            new_school_id = last_school.id + 1

            school_serializer = self.get_serializer(data=request.data, partial=True)
            school_serializer.is_valid(raise_exception=True)
            school_serializer.save(id=new_school_id)

        user = request.user
        if IsAdmin().has_permission(request, self):
            user.school.add(school_serializer.data['id'])
            user.save()
        return Response(school_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        try:
            instance = School.objects.get(id=kwargs['pk'])
        except School.DoesNotExist:
            return Response({'message': 'Школа не найдена'}, status=status.HTTP_403_FORBIDDEN)

        if instance.id not in request.user.school.all().values_list('id', flat=True):
            return Response({'message': 'Ваша школа не соответствует той, которую вы выбрали!'})

        if IsSuperAdmin().has_permission(request, self) or IsAdmin().has_permission(request, self):
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        else:
            return Response({'message': 'У вас нет прав доступа для изменения данных школы!'}, status=status.HTTP_403_FORBIDDEN)

    @action(["get"], detail=True, serializer_class=SchoolUsersSerializer, permission_classes=(permissions.IsAuthenticated, ))
    def users(self, request, pk, *args, **kwargs):
        """ Получение сотрудников школы """

        if IsAdmin().has_permission(request, self):
            user = request.user
            if user.school.filter(id=pk).exists():
                users = User.objects.filter(school=pk)
            else:
                return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        elif IsSuperAdmin().has_permission(request, self):
            users = User.objects.filter(school=pk)
        else:
            return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(users, many=True)

        return Response(serializer.data)

    @action(["get"], detail=True, serializer_class=SchoolParentsSerializer, permission_classes=(permissions.IsAuthenticated, ))
    def parents(self, request, pk, *args, **kwargs):
        if IsAdmin().has_permission(request, self):
            parents = User.objects.filter(role__role_name='Родитель', school=pk)
        elif IsSuperAdmin().has_permission(request, self):
            parents = User.objects.filter(role__role_name='Родитель')
        else:
            return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(parents, many=True)

        return Response(serializer.data)

    @action(["get"], detail=True, serializer_class=SchoolTeachersSerializer, permission_classes=(permissions.IsAuthenticated, ))
    def teachers(self, request, pk, *args, **kwargs):
        if IsAdmin().has_permission(request, self):
            teachers_role = User.objects.filter(role__role_name='Учитель', school=pk)
            user_is_teacher = User.objects.filter(user_info__is_teacher=True, school=pk)
            teachers = teachers_role | user_is_teacher
        elif IsSuperAdmin().has_permission(request, self):
            teachers_role = User.objects.filter(role__role_name='Учитель')
            user_is_teacher = User.objects.filter(user_info__is_teacher=True)
            teachers = teachers_role | user_is_teacher
        else:
            return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = SchoolTeachersSerializer(teachers, many=True)

        return Response(serializer.data)

    @action(["get"], detail=True, serializer_class=SchoolStudentsSerializer, permission_classes=(permissions.IsAuthenticated, ))
    def students(self, request, pk, *args, **kwargs):
        """ Получение студентов школы """

        if IsAdmin().has_permission(request, self):
            user = request.user
            if user.school.filter(id=pk).exists():
                students = Student.objects.filter(stud_class__school_id=pk)
            else:
                return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        elif IsSuperAdmin().has_permission(request, self):
            students = Student.objects.filter(stud_class__school_id=pk)
        else:
            return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(students, many=True)

        return Response(serializer.data)

    @action(["get"], detail=True, serializer_class=SchoolClassesSerializer, permission_classes=(permissions.IsAuthenticated, ))
    def classes(self, request, pk, *args, **kwargs):
        """ Получение классов школы """

        if IsAdmin().has_permission(request, self):
            user = request.user
            if user.school.filter(id=pk).exists():
                classes = Class.objects.filter(school_id=pk)
            else:
                return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        elif IsSuperAdmin().has_permission(request, self):
            classes = Class.objects.filter(school_id=pk)
        else:
            return Response({'message': 'У вас нет доступа к этому разделу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(classes, many=True)

        return Response(serializer.data)

    @action(["post"], detail=True, permission_classes=(permissions.IsAuthenticated, ))
    def create_class(self, request, pk, *args, **kwargs):
        """ Создание класса """

        class_service = ClassCreateService().class_create(request, pk)
        return class_service

    @action(["get"], detail=True, permission_classes=(permissions.IsAuthenticated, ))
    def report(self, request, *args, **kwargs):
        """ Отчеты школы по договорам """

        school = School.objects.get(id=kwargs['pk'])
        count_students = ContractMS.objects.using('ms_sql').filter(SchoolID=school.id).aggregate(Count('StudentID', distinct=True))['StudentID__count']

        count_study_contracts = ContractMS.objects.using('ms_sql').filter(SchoolID=school.id).count()
        count_food_contracts = ContractFoodMS.objects.using('ms_sql').filter(SchoolID=school.id).count()
        count_driver_contracts = ContractDriverMS.objects.using('ms_sql').filter(SchoolID=school.id).count()

        sum_study_contracts = ContractMS.objects.using('ms_sql').filter(SchoolID=school.id).aggregate(Sum('ContractSum'))
        sum_food_contracts = ContractFoodMS.objects.using('ms_sql').filter(SchoolID=school.id).aggregate(Sum('ContractSum'))
        sum_driver_contracts = ContractDriverMS.objects.using('ms_sql').filter(SchoolID=school.id).aggregate(Sum('ContractAmount'))

        if sum_study_contracts['ContractSum__sum'] is None:
            sum_study_contracts['ContractSum__sum'] = 0
        if sum_food_contracts['ContractSum__sum'] is None:
            sum_food_contracts['ContractSum__sum'] = 0
        if sum_driver_contracts['ContractAmount__sum'] is None:
            sum_driver_contracts['ContractAmount__sum'] = 0

        sum_arrears_study_contracts = Decimal(0)
        sum_arrears_food_contracts = 0
        sum_arrears_driver_contracts = 0

        contract_list = ContractMS.objects.using('ms_sql').filter(SchoolID=school.id).filter(ContractDate__year=2023)
        for contract in contract_list:
            arrears = ContractService(contract_list).get_value_of_arrears_with_contract_num(contract.ContractNum)
            sum_arrears_study_contracts += arrears['Arrears']

        # for contract in ContractFoodMS.objects.using('ms_sql').all():
        #     arrears = ContractService(ContractFoodMS.objects.using('ms_sql').filter(SchoolID=school.id)).get_value_of_arrears(contract.ContractNum)
        #     sum_arrears_food_contracts += arrears
        #
        # for contract in ContractDriverMS.objects.using('ms_sql').all():
        #     arrears = ContractService(ContractDriverMS.objects.using('ms_sql').filter(SchoolID=school.id)).get_value_of_arrears(contract.ContractNum)
        #     sum_arrears_driver_contracts += arrears

        count_all_contracts = count_study_contracts + count_food_contracts + count_driver_contracts
        sum_all_contracts = float(sum_study_contracts['ContractSum__sum']) + float(sum_food_contracts['ContractSum__sum']) + float(sum_driver_contracts['ContractAmount__sum'])
        sum_arrears_all_contracts = sum_arrears_study_contracts + sum_arrears_food_contracts + sum_arrears_driver_contracts

        data = {
            'count_students': count_students,
            'count_contracts': count_all_contracts,
            'sum_contracts': int(sum_all_contracts),
            'sum_arrears_contracts': int(sum_arrears_all_contracts)
        }

        return Response(dict(data))

    @action(["post"], detail=False)
    def migration_school_data(self, request, *args, **kwargs):
        """ Миграция данных школы из MS SQL """

        pin_code = request.data.get('pin_code')

        if pin_code == '1111':
            school_ms = SchoolMS.objects.using('ms_sql').all()
            school_pg = School.objects.all()

            for school in school_ms:
                School.objects.create(
                    id=school.id,
                    sSchool_logo=None,
                    sSchool_name=school.sSchool_name,
                    sSchool_address=school.sSchool_address,
                    sSchool_direct=school.sSchool_direct,
                    sSchool_language=school.sSchool_language,
                    isSchool=school.isSchool,
                    sCommentary=school.sCommentary,
                    sBin=school.sBin
                )

            return Response({'message': 'ok'})
        else:
            return Response({'message': 'Не удалось загрузить данные'}, status=status.HTTP_403_FORBIDDEN)


class SchoolRequisitesView(ModelViewSet):
    """ API для реквизитов школы """

    queryset = SchoolRequisites.objects.all()
    serializer_class = SchoolRequisitesSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get', 'post', 'put', 'delete']

    def create(self, request, *args, **kwargs):
        try:
            school = School.objects.get(id=request.data.get('school'))
        except School.DoesNotExist:
            return Response({'message': 'Школа не найдена'}, status=status.HTTP_403_FORBIDDEN)

        if SchoolRequisites.objects.filter(school=school).exists():
            return Response({'message': 'Реквизиты школы уже существуют'}, status=status.HTTP_403_FORBIDDEN)

        request.data['school'] = school.id

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()  # Получаем объект реквизитов

        school = request.data.get('school')

        if school:
            try:
                instance.school = School.objects.get(id=school)
            except School.DoesNotExist:
                return Response({'message': 'Школа не найдена'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class ClassViewSet(ModelViewSet):
    """ API для классов """

    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        teacher = request.data.get('teacher')
        if teacher:
            print("teacher", teacher)
            try:
                user = User.objects.get(id=teacher)
                request.data['teacher'] = user.id
                if UserInfo.objects.filter(user=user).first().is_teacher is False and user.role.role_name != 'Учитель':
                    return Response({'message': 'Выбранный пользователь не является учителем!'}, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                return Response({'message': 'Учитель не найден!'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateClassSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(["post"], detail=False, serializer_class=UpdateStudentClasses)
    def update_student_classes(self, request, *args, **kwargs):
        """ Обновление классов студентов """

        students = request.data.get('students')
        class_id = request.data.get('class_id')
        teacher = request.data.get('teacher')

        with transaction.atomic():
            try:
                statement_teacher = User.objects.filter(id=teacher).first()
                if statement_teacher:
                    if statement_teacher.role.role_name != 'Учитель':
                        return Response({'message': 'Пользователь не является учителем'}, status=status.HTTP_403_FORBIDDEN)
                    class_object = Class.objects.get(id=class_id)
                    class_object.teacher = statement_teacher
                    class_object.save()

                    if class_object.school_id in statement_teacher.school.all():
                        pass
                    else:
                        statement_teacher.school.add(class_object.school.id)
                        statement_teacher.save()
            except Class.DoesNotExist:
                return Response({'message': 'Класс не найден'}, status=status.HTTP_403_FORBIDDEN)
            for student_id in students:
                try:
                    statement_student = Statement.objects.get(id=student_id)
                    student_class_change = Student.objects.filter(iin=statement_student.iin)

                    if student_class_change.exists():
                        for stud in student_class_change:
                            stud.stud_class = Class.objects.get(id=class_id)
                            print(stud)
                            stud.save()
                    else:
                        student = Student.objects.create(
                            id_from_ms=None,
                            photo_avatar=statement_student.student_image,
                            birthday=statement_student.birthday,
                            full_name=f'{statement_student.full_name}',
                            iin=statement_student.iin,
                            parent=User.objects.get(id=statement_student.parent.id) if statement_student.parent else None,
                            stud_class=Class.objects.get(id=class_id) if class_id else None,
                            leave=None,
                            reason_leave=None,
                            sex=None,
                            email=None,
                            phone=None,
                        )
                except Statement.DoesNotExist:
                    return Response({'message': 'Заявление студента не найдено'})

                except Class.DoesNotExist:
                    return Response({'message': 'Класс не найден'})

                except MultipleObjectsReturned:
                    return Response({'message': 'Найдено несколько студентов с одинаковым ИИН'})

            return Response({'message': 'ok'})
