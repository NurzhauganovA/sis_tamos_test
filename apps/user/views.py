from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import \
    UserRole,\
    User, \
    AdditionalParent, \
    UserInfo
from .permissions import IsAdmin, IsSuperAdmin
from .serializers import \
    UserRoleSerializer, \
    UserSerializer, \
    AdditionalParentSerializer, \
    UserInfoSerializer, UserStatusSerializer, UserActivationSerializer, UserPasswordSerializer, UserPhoneSerializer, \
    UserVerifyCodeSerializer, UserDeleteSerializer, UserActivationSendSMSSerializer
from .serializers.jwt import CustomTokenObtainPairSerializer
from .services import UserCreateService, UserStatusService, UserActivateService, AdditionalParentCreateService, \
    UserViewProfileService, UserChangeProfileService, UserSendSMSToPhoneService, UserVerifySMSCodeService, \
    SetNewPasswordService, UserUpdateService
from .utils import send_activation_code
from ..school.models import School


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserRoleView(viewsets.ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    http_method_names = ['get', 'post', 'put', 'delete']


class UserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    create_service = UserCreateService
    update_service = UserUpdateService
    status_service = UserStatusService
    activate_service = UserActivateService

    def create(self, request, *args, **kwargs):
        new_user = self.create_service().user_create(request)

        return new_user

    def update(self, request, *args, **kwargs):
        user = self.update_service().user_update(request, *args, **kwargs)

        return user

    @action(["post"], detail=False, serializer_class=UserSerializer)
    def create_parent(self, request, *args, **kwargs):
        new_user = self.create_service().parent_create(request)

        return new_user

    @action(["post"], detail=False, permission_classes=[IsAuthenticated], serializer_class=UserDeleteSerializer)
    def delete_request_user(self, request, *args, **kwargs):
        user = User.objects.get(id=request.user.id)
        user.is_deleted = True
        user.is_active = False
        user.reason_for_deletion = request.data.get('reason_for_deletion')
        user.save()

        return Response({'message': 'User deleted successfully'})

    @action(["post"], detail=False, serializer_class=UserStatusSerializer)
    def user_status(self, request, *args, **kwargs):
        user_status = self.status_service().user_status(request)

        return user_status

    @action(["post"], detail=False, serializer_class=UserActivationSerializer)
    def activate_user(self, request, *args, **kwargs):
        activate_user = self.activate_service().user_activate(request)

        return activate_user

    @action(["post"], detail=False, serializer_class=UserActivationSendSMSSerializer)
    def send_sms_for_user_activate(self, request, *args, **kwargs):
        activate_user = self.activate_service().send_sms_for_user_activate(request)

        return activate_user


class UserInfoView(viewsets.ModelViewSet):
    queryset = UserInfo.objects.all()
    serializer_class = UserInfoSerializer
    http_method_names = ['get', 'post', 'put']
    create_service = UserCreateService

    def create(self, request, *args, **kwargs):
        new_user_info = self.create_service().user_info_create(request)

        return new_user_info


class AdditionalParentView(viewsets.ModelViewSet):
    queryset = AdditionalParent.objects.all()
    serializer_class = AdditionalParentSerializer
    http_method_names = ['get', 'post', 'put']
    create_service = AdditionalParentCreateService

    def get_permissions(self):
        permission_classes = [IsAuthenticated]
        if self.action == 'create' or self.action == 'retrieve' or self.action == 'update':
            permission_classes = []

        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        new_additional_parent = self.create_service().additional_parent_create(request)

        return new_additional_parent


class UserProfileView(viewsets.ViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    view_profile_service = UserViewProfileService
    change_profile_service = UserChangeProfileService
    send_sms_to_phone_service = UserSendSMSToPhoneService
    verify_sms_code_service = UserVerifySMSCodeService
    set_new_password_service = SetNewPasswordService

    @action(["get"], detail=False, permission_classes=[IsAuthenticated])
    def view_profile(self, request, *args, **kwargs):
        view_profile = self.view_profile_service().view_profile(request)
        return view_profile

    @action(["put"], detail=False, permission_classes=[IsAuthenticated])
    def change_profile(self, request, *args, **kwargs):
        change_profile = self.change_profile_service().change_profile(request)
        return change_profile

    @action(["post"], detail=False, serializer_class=UserPhoneSerializer, permission_classes=[AllowAny])
    def send_sms_to_phone(self, request, *args, **kwargs):
        send_sms_to_phone = self.send_sms_to_phone_service().send_sms_to_phone(request)
        return send_sms_to_phone

    @action(["post"], detail=False, serializer_class=UserVerifyCodeSerializer, permission_classes=[AllowAny])
    def verify_sms_code(self, request, *args, **kwargs):
        verify_sms_code = self.verify_sms_code_service().verify_sms_code(request)
        return verify_sms_code

    @action(["post"], detail=False, serializer_class=UserPasswordSerializer, permission_classes=[AllowAny])
    def set_new_password(self, request, *args, **kwargs):
        set_new_password = self.set_new_password_service().set_new_password(request)
        return set_new_password

    @action(["post"], detail=False, permission_classes=[AllowAny])
    def check_email_exists(self, request, *args, **kwargs):
        email = request.data.get('email')

        if UserInfo.objects.filter(email=email).exists():
            return Response({'exists': True})
        return Response({'exists': False})

    @action(["post"], detail=False, permission_classes=[AllowAny])
    def check_phone_exists(self, request, *args, **kwargs):
        login = request.data.get('login')

        if User.objects.filter(login=login).exists():
            return Response({'exists': True})
        return Response({'exists': False})

    @action(["post"], detail=False, permission_classes=[AllowAny])
    def check_iin_exists(self, request, *args, **kwargs):
        iin = request.data.get('iin')

        if UserInfo.objects.filter(iin=iin).exists():
            return Response({'exists': True})
        return Response({'exists': False})
