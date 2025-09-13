from rest_framework import serializers
from apps.contract.models import ContractMS
from apps.school.serializers.stud_class import ClassSerializer
from apps.student.models import Student


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['full_name']


class KaspiIntegrationFieldsSerializer(serializers.ModelSerializer):
    StudentID = StudentSerializer(read_only=True)
    ClassID = ClassSerializer(read_only=True)

    class Meta:
        model = ContractMS
        fields = ['ContractNum', 'StudentID', 'ClassID']
