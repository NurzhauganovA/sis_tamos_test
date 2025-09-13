from rest_framework import serializers
from ..models import Student
from ...contract.models import ContractMS, StudentMS, ClassMS
from ...user.models import ParentMS, User, UserRole
from ...user.serializers import AdditionalParentSerializer, UserSerializer


class CreateStudentSerializer(serializers.ModelSerializer):
    additional_parent = AdditionalParentSerializer(read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'photo_avatar', 'full_name', 'iin', 'birthday', 'parent', 'additional_parent', 'email', 'phone', 'stud_class']
        kwargs = {
            'iin': {'required': True},
            'birthday': {'required': True},
            'full_name': {'required': True}
        }


class StudentParentMSSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        user_role = UserRole.objects.filter(id=obj.role_id).first()
        data = {
            'id': user_role.id,
            'role_name': user_role.role_name
        }

        return data

    class Meta:
        model = User
        fields = ('id', 'login', 'fio', 'is_work', 'is_active', 'is_deleted', 'role')


class StudentSerializer(serializers.ModelSerializer):
    id_from_ms = serializers.SerializerMethodField()
    photo_avatar = serializers.SerializerMethodField()
    stud_class = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    def get_id_from_ms(self, obj):
        return int(StudentMS.objects.using('ms_sql').get(id=obj.id).id)

    @staticmethod
    def get_photo_avatar(obj):
        return None

    def get_stud_class(self, obj):
        contract = ContractMS.objects.using('ms_sql').filter(StudentID=obj.id).order_by('-ContractDate').first()
        if contract:
            try:
                contract_class = ClassMS.objects.using('ms_sql').filter(id=contract.ClassID.id).first()
                return f'{contract_class.class_num} {contract_class.class_liter}'
            except AttributeError:
                return None
            except TypeError:
                return None
        else:
            return None

    def get_parent(self, obj):
        parent_ms = ParentMS.objects.using('ms_sql').filter(id=obj.parent_id.id).first()
        login_format = f'+7{parent_ms.phone}'
        parent = User.objects.filter(login=login_format).first()
        if parent:
            return UserSerializer(parent).data
        else:
            return None

    class Meta:
        model = StudentMS
        fields = ('id', 'id_from_ms', 'photo_avatar', 'birthday', 'full_name', 'iin', 'leave', 'reason_leave', 'sex', 'email', 'phone', 'parent', 'stud_class')
