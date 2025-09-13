from django.core.cache import cache
from django.db import transaction
from rest_framework import status, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .permissions import IsAdmin, IsSuperAdmin
from .tests import UploadStudentDataFromMSSQL
from ..school.models import School
from .models import User, UserRole, UserInfo, UserMS, UserDocFile, ParentMS
from .serializers import UserSerializer, UserInfoSerializer, AdditionalParentSerializer, UserUpdateSerializer, \
    UserCreateSerializer
from .utils import send_activation_code, send_reset_password_code
from ..student.models import Student


class UserCreateService:
    @staticmethod
    def user_create(request):
        request_data = request.data.copy()
        request.data['school'] = request_data.pop('school', [])
        try:
            request.data['role'] = UserRole.objects.get(id=request_data.pop('role')).id
        except UserRole.DoesNotExist:
            return Response({'message': 'Роль не найден!'}, status=status.HTTP_403_FORBIDDEN)

        try:
            for school_id in request.data['school']:
                School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'message': 'Школа не найдена!'}, status=status.HTTP_403_FORBIDDEN)

        user_login = request.data['login'].split('+7')[1]
        if UserMS.objects.using('ms_sql').filter(login=user_login).exists():
            return Response({'message': 'Вы уже зарегистированы на нашем системе!'}, status=status.HTTP_403_FORBIDDEN)

        user_serializer = UserCreateSerializer(data=request_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user = User.objects.create_user(**user_serializer.validated_data)

        user.role = UserRole.objects.get(id=request.data['role'])
        user.is_active = False
        user.set_password(request.data['password'])

        user.save()
        for school_id in request.data['school']:
            school = School.objects.get(id=school_id)
            user.school.add(school)

        user_info = UserInfo.objects.filter(user=user).first()
        if user_info:
            pass
        else:
            user_info = UserInfo.objects.create(
                user=user,
                is_teacher=True if user.role.role_name == 'Учитель' else False
            )

        send_activation_code(user)

        new_serializer = UserSerializer(user)

        return Response(new_serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def parent_create(request):
        request_data = request.data.copy()
        request.data._mutable = True

        request.data['school'] = request_data.pop('school', [])

        user_serializer = UserCreateSerializer(data=request_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user = User.objects.create_user(**user_serializer.validated_data)

        user.role = UserRole.objects.get(role_name='Родитель')

        is_active = request.data.get('is_active')
        print(is_active)

        if is_active == 'true':
            user.is_active = True
        else:
            user.is_active = False

        user.save()

        for school_id in request.data['school']:
            school = School.objects.get(id=school_id)
            user.school.add(school)

        send_activation_code(user)

        request.data['user'] = user.id

        parent_info_serializer = UserInfoSerializer(data=request.data, partial=True)
        parent_info_serializer.is_valid(raise_exception=True)
        parent_info_instance = parent_info_serializer.save(user=user)

        parent_info_serializer.save(user=user)

        serialized_user = UserSerializer(user).data
        serialized_parent_info = parent_info_serializer.data
        serialized_user['user_info'] = serialized_parent_info

        return Response(serialized_user, status=status.HTTP_201_CREATED)

    @staticmethod
    def user_info_create(request):
        try:
            request.data['user'] = User.objects.get(id=request.data.get('user')).id
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)

        user_info_serializer = UserInfoSerializer(data=request.data, partial=True)
        user_info_serializer.is_valid(raise_exception=True)
        user_info_serializer.save()

        return Response(user_info_serializer.data, status=status.HTTP_201_CREATED)


class UserUpdateService:
    def user_update(self, request, *args, **kwargs):
        try:
            user = User.objects.get(id=kwargs['pk'])
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)

        user_school_list = user.school.all().values_list('id', flat=True)
        request_user_school_list = request.user.school.all().values_list('id', flat=True)

        if not user_school_list and not IsSuperAdmin().has_permission(request, self):
            return Response({'message': 'У выбранного пользователя нет связанной школы!'}, status=status.HTTP_403_FORBIDDEN)

        for user_school_id in user_school_list:
            if user_school_id not in request_user_school_list and not IsSuperAdmin().has_permission(request, self):
                return Response({'message': 'У вас нет прав для выполнения этого действия!'},
                                status=status.HTTP_403_FORBIDDEN)

        if IsAdmin().has_permission(request, self) or IsSuperAdmin().has_permission(request, self):
            user_serializer = UserUpdateSerializer(user, data=request.data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

            user_info = UserInfo.objects.filter(user=user).first()

            if not user_info:
                user_info = UserInfo.objects.create(user=user)

            user_info_serializer = UserInfoSerializer(user_info, data=request.data, partial=True)
            user_info_serializer.is_valid(raise_exception=True)
            user_info_serializer.save()

            if 'photo_avatar' in request.data:
                user_info.photo_avatar = request.data['photo_avatar']
                user_info.save()

            if request.data.get('uploaded_files'):
                user_info_doc_files = UserDocFile.objects.filter(user=user_info)
                user_info_doc_files.delete()

                uploaded_files = request.data.pop('uploaded_files', None)
                if uploaded_files:
                    user_files = [
                        UserDocFile(user=user_info, file=file) for file in uploaded_files
                    ]

                    for file in user_files:
                        file.full_clean()

                    try:
                        with transaction.atomic():
                            UserDocFile.objects.bulk_create(user_files)
                    except ValidationError as e:
                        raise serializers.ValidationError(str(e))

            return Response(UserSerializer(user).data)
        else:
            return Response({'message': 'У вас нет прав для выполнения этого действия!'},
                            status=status.HTTP_403_FORBIDDEN)


class UserStatusService:
    @staticmethod
    def user_status(request):
        user_login = request.data['login']
        user = User.objects.get(login=user_login)
        return Response({'status': 1 if user.is_active else 0})


class UserActivateService:
    @staticmethod
    def user_activate(request):
        user_login, code = request.data['login'], request.data['code']
        cache_code = cache.get(f'user_activation_{user_login}')

        if cache_code == code:
            user = User.objects.get(login=user_login)
            user.is_active = True
            user.save()

            token_data = TokenObtainPairSerializer()

            data = {
                'refresh': str(token_data.get_token(user)),
                'access': str(token_data.get_token(user).access_token)
            }

            cache.delete(f'user_activation_{user_login}')

            return Response(data, status=status.HTTP_200_OK)

        return Response({'error': 'login or code is incorrect!'}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def send_sms_for_user_activate(request):
        user_login = request.data['login']
        user = User.objects.get(login=user_login)

        cache.delete(f'user_activation_{user_login}')

        send_activation_code(user)

        return Response({'successful': 'SMS send to user'}, status=status.HTTP_200_OK)


class AdditionalParentCreateService:
    @staticmethod
    def additional_parent_create(request):
        data = request.data.copy()
        try:
            request.data['main_user'] = User.objects.get(id=data['main_user'])
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({'error': 'Main user id not received'}, status=status.HTTP_400_BAD_REQUEST)

        additional_parent_serializer = AdditionalParentSerializer(data=data)
        additional_parent_serializer.is_valid(raise_exception=True)
        additional_parent_serializer.save()
        return Response(additional_parent_serializer.data, status=status.HTTP_201_CREATED)


class UserViewProfileService:
    @staticmethod
    def view_profile(request):
        user = request.user
        parent_info = UserInfo.objects.filter(user=user).first()
        user.parent_info = parent_info

        return Response(UserSerializer(user).data)


class UserChangeProfileService:
    @staticmethod
    def change_profile(request):
        user = request.user
        user_serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        user_info = UserInfo.objects.filter(user=user).first()
        user_info_serializer = UserInfoSerializer(user_info, data=request.data, partial=True)
        user_info_serializer.is_valid(raise_exception=True)
        user_info_serializer.save()

        if 'photo_avatar' in request.data:
            user_info.photo_avatar = request.data['photo_avatar']
            user_info.save()

        if request.data.get('uploaded_files'):
            user_info_doc_files = UserDocFile.objects.filter(user=user_info)
            user_info_doc_files.delete()

            uploaded_files = request.data.pop('uploaded_files', None)
            if uploaded_files:
                user_files = [
                    UserDocFile(user=user_info, file=file) for file in uploaded_files
                ]

                for file in user_files:
                    file.full_clean()

                try:
                    with transaction.atomic():
                        UserDocFile.objects.bulk_create(user_files)
                except ValidationError as e:
                    raise serializers.ValidationError(str(e))

        return Response(UserSerializer(user).data)


class UserSendSMSToPhoneService:
    @staticmethod
    def send_sms_to_phone(request):
        login = request.data.get('login')
        login_ms_format = login.split('+7')[1]

        print("login - 300", login)
        print("login_ms_format - 301", login_ms_format)

        if login:
            try:
                user = User.objects.get(login=login)
                print("user - 306", user)
            except User.DoesNotExist:
                try:
                    user = UserMS.objects.using('ms_sql').get(login=login_ms_format)
                    print("user - 310", user)
                except UserMS.DoesNotExist:
                    try:
                        user = ParentMS.objects.using('ms_sql').get(phone=login_ms_format)
                        print("user - 314", user)
                    except ParentMS.DoesNotExist:
                        return Response({'error': 'К сожалению вы не зарегистрированы в нашей системе!'}, status=status.HTTP_403_FORBIDDEN)

            send_reset_password_code(user)

            return Response({'successful': 'SMS send to user'}, status=status.HTTP_200_OK)

        return Response({'error': 'Phone request data not received'}, status=status.HTTP_400_BAD_REQUEST)


class UserVerifySMSCodeService:
    @staticmethod
    def verify_sms_code(request):
        user_login, code = request.data.get('login'), request.data.get('code')
        cache_code = cache.get(f'reset_password_{user_login}')

        if cache_code is None:
            user_login = user_login.split('+7')[1]
            cache_code = cache.get(f'reset_password_{user_login}')

        if cache_code == code:
            return Response({'successful': 'SMS code is correct!'}, status=status.HTTP_200_OK)
        return Response({'error': 'SMS code is incorrect!'}, status=status.HTTP_400_BAD_REQUEST)


class SetNewPasswordService:
    @staticmethod
    def set_new_password(request):
        login = request.data.get('login')
        password = request.data.get('password')

        try:
            user = User.objects.get(login=login)
            user.set_password(password)
            user.save()
        except User.DoesNotExist:
            try:
                login_ms_format = login.split('+7')[1]

                user_ms = UserMS.objects.using('ms_sql').filter(login=login_ms_format).first()
                parent_ms = ParentMS.objects.using('ms_sql').filter(phone=login_ms_format).first()

                if user_ms is not None:
                    user = User.objects.create_user(
                        login=login,
                        is_active=True,
                        role=UserRole.objects.get(role_name='Родитель') if user_ms.role_id == 0 else None,
                        fio=user_ms.fio,
                        is_work=True if user_ms.iswork == 1 else False
                    )
                    user.set_password(password)
                    user.save()
                elif parent_ms is not None:
                    user = User.objects.create_user(
                        login=login,
                        is_active=True,
                        role=UserRole.objects.get(role_name='Родитель'),
                        fio=parent_ms.full_name,
                        is_work=False
                    )
                    user.set_password(password)
                    user.save()
                else:
                    return Response({'error': 'К сожалению вы не зарегистрированы в нашей системе!'}, status=status.HTTP_403_FORBIDDEN)

                def clean_null_bytes(value):
                    return str(value).replace('\x00', '') if value else value

                parent_ms_data_cleaned = {
                    'address': clean_null_bytes(parent_ms.address) if parent_ms else None,
                    'contacts': clean_null_bytes(parent_ms.contacts) if parent_ms else None,
                    'email': clean_null_bytes(parent_ms.email) if parent_ms else None,
                    'iin': clean_null_bytes(parent_ms.iin) if parent_ms else None,
                    'num_of_doc': clean_null_bytes(parent_ms.num_of_doc) if parent_ms else None,
                    'issued_by': clean_null_bytes(parent_ms.issued_by) if parent_ms else None,
                    'issue_date': parent_ms.issue_date if parent_ms else None,
                    'work_place': clean_null_bytes(parent_ms.work_place) if parent_ms else None,
                    'work_position': clean_null_bytes(parent_ms.work_position) if parent_ms else None
                }

                UserInfo.objects.create(
                    user=user,
                    **parent_ms_data_cleaned
                )

                try:
                    user.fio = parent_ms.full_name
                except AttributeError:
                    user.fio = 'Родитель'
                user.save()

            except UserMS.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)

        return Response({'successful': 'Password successfully changed'}, status=status.HTTP_200_OK)
