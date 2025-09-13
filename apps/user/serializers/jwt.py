from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from ..exceptions import UserNotActive, UserNotFound, UserCredentialsError, UserPasswordNotSet
from ..models import User, UserMS, UserRole, ParentMS, UserInfo


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        login, password = attrs['login'], attrs['password']

        user = User.objects.filter(login=login).first()
        print("user", user)

        if user is not None:
            if not user.is_active:
                raise UserNotActive

            try:
                return super().validate(attrs)
            except AuthenticationFailed:
                raise UserCredentialsError

        if user is None:
            login_ms_format = login.split('+7')[1]

            user_ms = UserMS.objects.using('ms_sql').filter(login=login_ms_format).first()
            parent_ms = ParentMS.objects.using('ms_sql').filter(phone=login_ms_format).first()

            if user_ms is not None:
                raise UserPasswordNotSet
            else:
                raise UserNotFound

        return self.validate(attrs)
