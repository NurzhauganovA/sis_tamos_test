from rest_framework import serializers

from .user_info import UserInfoSerializer
from .user_role import UserRoleSerializer
from ..models import User, UserInfo
from ...school.serializers import SchoolSerializer


class UserSerializer(serializers.ModelSerializer):
    school = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    user_info = UserInfoSerializer(read_only=True)

    def get_school(self, obj):
        return SchoolSerializer(obj.school, many=True).data

    def get_role(self, obj):
        return UserRoleSerializer(obj.role).data

    class Meta:
        model = User
        fields = ['id', 'login', 'fio', 'is_work', 'is_active', 'is_deleted', 'role', 'school', 'user_info']


class UserCreateSerializer(serializers.ModelSerializer):
    school = serializers.ListSerializer(child=serializers.IntegerField(), required=False, source='school.id')

    class Meta:
        model = User
        fields = ['id', 'school', 'role', 'login', 'fio', 'is_work']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'school', 'role', 'login', 'fio', 'is_work']


class UserDeleteSerializer(serializers.ModelSerializer):
    reason_for_deletion = serializers.CharField()

    class Meta:
        model = User
        fields = ['id', 'reason_for_deletion']


class UserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['login']


class UserActivationSerializer(serializers.ModelSerializer):
    code = serializers.IntegerField()

    class Meta:
        model = User
        fields = ['login', 'code']


class UserActivationSendSMSSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['login']


class UserVerifyCodeSerializer(serializers.ModelSerializer):
    code = serializers.IntegerField()

    class Meta:
        model = User
        fields = ['login', 'code']


class UserPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['login']


class UserPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['login', 'password']
