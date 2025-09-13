from rest_framework import serializers
from ..models import School, SchoolRequisites, Class
from ...statement.models import Statement
from ...student.models import Student
from ...user.models import User, UserInfo
from ...user.serializers.user_info import UserInfoSerializer
from ...user.serializers.user_role import UserRoleSerializer


class CreateSchoolSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания школы """

    class Meta:
        model = School
        fields = '__all__'
        extra_kwargs = {
            'sSchool_name': {'required': True},
        }


class SchoolSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения школы """

    class Meta:
        model = School
        fields = ['id', 'sSchool_logo', 'sSchool_name', 'sSchool_address', 'sSchool_direct', 'sSchool_language', 'isSchool', 'sCommentary', 'sBin']


class SchoolClassSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения классов школы """

    class Meta:
        model = Class
        fields = ['class_num', 'class_liter']


class UserWithoutSchoolSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения пользователей без школы """

    role = serializers.SerializerMethodField()
    user_info = UserInfoSerializer(read_only=True)

    def get_school(self, obj):
        return SchoolSerializer(obj.school, many=True).data

    def get_role(self, obj):
        return UserRoleSerializer(obj.role).data

    class Meta:
        model = User
        fields = ['id', 'login', 'fio', 'is_work', 'is_active', 'is_deleted', 'role', 'school', 'user_info']


class SchoolUsersSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения сотрудников школы """

    role = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()

    def get_role(self, obj):
        return obj.role.role_name

    def get_user_info(self, obj):
        return UserInfoSerializer(UserInfo.objects.filter(user=obj.id).first()).data

    class Meta:
        model = User
        fields = ['id', 'login', 'fio', 'role', 'user_info']


class ChildrenSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения детей """

    class Meta:
        model = Student
        fields = ['id', 'photo_avatar', 'full_name', 'iin', 'birthday', 'email', 'phone', 'stud_class']


class SchoolParentsSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения родителей школы """

    user_info = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    def get_user_info(self, obj):
        return UserInfoSerializer(UserInfo.objects.filter(user=obj.id).first()).data

    def get_role(self, obj):
        return obj.role.role_name

    def get_children(self, obj):
        children = []
        students = Student.objects.filter(parent=obj.id)
        statements = Statement.objects.filter(parent=obj.id)
        for student in students:
            children.append(SchoolStudentsSerializer(student).data)
        for statement in statements:
            if statement.iin in [child['iin'] for child in children]:
                continue
            else:
                children.append(SchoolStatementsSerializer(statement).data)
        return ChildrenSerializer(children, many=True).data

    class Meta:
        model = User
        fields = ['id', 'fio', 'login', 'role', 'user_info', 'children']


class SchoolTeachersSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения учителей школы """

    role = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()

    def get_role(self, obj):
        return obj.role.role_name

    def get_user_info(self, obj):
        return UserInfoSerializer(UserInfo.objects.filter(user=obj.id).first()).data

    class Meta:
        model = User
        fields = ['id', 'fio', 'login', 'role', 'user_info']


class SchoolStudentsSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения учеников школы """

    stud_class = SchoolClassSerializer(read_only=True)
    parent = serializers.SerializerMethodField()

    def get_parent(self, obj):
        return SchoolTeachersSerializer(obj.parent).data

    class Meta:
        model = Student
        fields = ['id', 'photo_avatar', 'full_name', 'iin', 'birthday', 'stud_class', 'email', 'phone', 'parent']


class SchoolStatementsSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения заявлений школы """

    parent = serializers.SerializerMethodField()

    def get_parent(self, obj):
        return SchoolTeachersSerializer(obj.parent).data

    class Meta:
        model = Statement
        fields = ['id', 'full_name', 'iin', 'birthday', 'num_of_doc', 'is_nutrition', 'is_transport', 'student_class', 'student_image', 'parent']


class SchoolClassesTeacherSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения классов школы для учителя """

    teacher = SchoolTeachersSerializer(read_only=True)

    class Meta:
        model = Class
        fields = ['id', 'class_num', 'class_liter', 'teacher']


class SchoolClassesSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения классов школы """

    teacher = SchoolTeachersSerializer(read_only=True)
    students = serializers.SerializerMethodField()

    def get_students(self, obj):
        students = Student.objects.filter(stud_class=obj)
        return SchoolStudentsSerializer(students, many=True).data

    class Meta:
        model = Class
        fields = ['id', 'class_num', 'class_liter', 'max_class_num', 'teacher', 'students']


class SchoolRequisitesSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения реквизитов школы """

    school = SchoolSerializer(read_only=True)

    class Meta:
        model = SchoolRequisites
        fields = ['id', 'school', 'bank_name', 'bank_address', 'bank_bik', 'bank_iik', 'bank_kbe', 'bank_rs', 'bank_ks', 'bank_bin']
