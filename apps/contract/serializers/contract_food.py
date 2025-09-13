from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .contract import PaymentTypeMSSerializer, ContractStatusMSSerializer, EduYearMSSerializer, \
    SchoolMSSerializer, ClassMSSerializer, DiscountMSSerializer
from .student import StudentMSSerializer
from ..models import ContractFoodMS, ContractFoodDiscountMS


class ContractFoodDiscountMSSerializer(ModelSerializer):
    DiscountID = DiscountMSSerializer(read_only=True)

    class Meta:
        model = ContractFoodDiscountMS
        fields = ['DiscountID', 'DiscountSum']


class ContractFoodSerializer(ModelSerializer):
    Arrears = serializers.IntegerField(read_only=True)
    StudentID = StudentMSSerializer(read_only=True)
    PaymentTypeID = PaymentTypeMSSerializer(read_only=True)
    ContractStatusID = ContractStatusMSSerializer(read_only=True)
    EduYearID = EduYearMSSerializer(read_only=True)
    SchoolID = SchoolMSSerializer(read_only=True)
    ClassID = ClassMSSerializer(read_only=True)
    Discount = ContractFoodDiscountMSSerializer(read_only=True)

    class Meta:
        model = ContractFoodMS
        fields = ['id', 'StudentID', 'ContractDate', 'ContractDateClose', 'ContractNum', 'ContractAmount',
                  'PaymentTypeID', 'ContractStatusID', 'EduYearID', 'SchoolID', 'ClassID', 'Arrears', 'Discount'
                  ]
