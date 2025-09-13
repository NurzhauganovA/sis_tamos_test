from rest_framework import serializers
from ..models import Class
from ..serializers import SchoolSerializer
from ...student.models import Student
from ...user.serializers import UserSerializer


class StudentClassSerializer(serializers.ModelSerializer):
    """ Сериализатор для классов студентов """

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'birthday']


class ClassSerializer(serializers.ModelSerializer):
    """ Сериализатор для классов """

    school = SchoolSerializer(read_only=True)
    teacher = UserSerializer(read_only=True)
    students = serializers.SerializerMethodField()

    def get_students(self, obj):
        """ Добавить список студентов в класс """

        students = Student.objects.filter(stud_class=obj)
        return StudentClassSerializer(students, many=True).data

    class Meta:
        model = Class
        fields = ['id', 'class_num', 'class_liter', 'school', 'teacher', 'isGraduated', 'students']


class CreateClassSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания классов """

    class Meta:
        model = Class
        fields = ['id', 'class_num', 'class_liter', 'school', 'teacher', 'isGraduated']


class UpdateStudentClasses(serializers.ModelSerializer):
    """ Сериализатор для обновления классов студентов """

    students = serializers.ListSerializer(child=serializers.IntegerField())
    class_id = serializers.IntegerField()

    class Meta:
        model = Class
        fields = ['students', 'class_id']
