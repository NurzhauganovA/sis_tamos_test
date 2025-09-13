from rest_framework import serializers

from .contract import PaymentTypeMSSerializer, ContractStatusMSSerializer, EduYearMSSerializer, \
    SchoolMSSerializer, ClassMSSerializer
from .student import StudentMSSerializer
from ..models import ContractDriverMS


class ContractDriverSerializer(serializers.ModelSerializer):
    Arrears = serializers.IntegerField(read_only=True)
    StudentID = StudentMSSerializer(read_only=True)
    PaymentTypeID = PaymentTypeMSSerializer(read_only=True)
    ContractStatusID = ContractStatusMSSerializer(read_only=True)
    EduYearID = EduYearMSSerializer(read_only=True)
    SchoolID = SchoolMSSerializer(read_only=True)
    ClassID = ClassMSSerializer(read_only=True)

    class Meta:
        model = ContractDriverMS
        fields = ['id', 'StudentID', 'ContractDate', 'ContractDateClose', 'ContractNum', 'ContractAmount',
                  'PaymentTypeID', 'ContractStatusID', 'EduYearID', 'SchoolID', 'ClassID', 'Arrears'
                  ]
