from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from ..models import ContractMS, ClassMS, PaymentTypeMS, ContractStatusMS, \
    CompanyMS, EduYearMS, DiscountMS, DiscountTypeMS, ContractDiscountMS, ContractMonthPayMS, ContractDopMS
from ..serializers.student import StudentMSSerializer
from ...school.models import SchoolMS
from ...user.models import UserMS
from django.db.models import Sum


class SchoolMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о школе """

    class Meta:
        model = SchoolMS
        fields = ['sSchool_name', 'sSchool_address', 'sBin']


class ClassMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о классе """

    school_id = SchoolMSSerializer(read_only=True)

    class Meta:
        model = ClassMS
        fields = ['class_num', 'class_liter', 'school_id']


class PaymentTypeMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о типе оплаты """

    class Meta:
        model = PaymentTypeMS
        fields = ['sPaymentType']


class ContractStatusMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о текущем статусе договора """

    class Meta:
        model = ContractStatusMS
        fields = ['sStatusName']


class CompanyMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о компании """

    class Meta:
        model = CompanyMS
        fields = ['name', 'bank', 'bik', 'bin', 'iik']


class EduYearMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных об учебном годе """

    class Meta:
        model = EduYearMS
        fields = ['sEduYear']


class DiscountTypeMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о типе скидки """

    class Meta:
        model = DiscountTypeMS
        fields = ['sDiscountType']


class DiscountMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о скидке """

    iDiscountType = DiscountTypeMSSerializer(read_only=True)

    class Meta:
        model = DiscountMS
        fields = ['sDiscountName', 'iDiscountPercent', 'iDiscountType']


class ContractDiscountMSSerializer(ModelSerializer):
    DiscountID = DiscountMSSerializer(read_only=True)

    class Meta:
        model = ContractDiscountMS
        fields = ['DiscountID', 'DiscountSum']


class ContractMonthPayMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о месячных платежах """

    class Meta:
        model = ContractMonthPayMS
        fields = ['PayDateM', 'MonthAmount', 'MonthSum', 'QuarterDig']


class UserMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о пользователе """

    class Meta:
        model = UserMS
        fields = ['login', 'fio']


class ContractDopMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о дополнительных договорах """
    user_id = UserMSSerializer(read_only=True)
    status_id = serializers.SerializerMethodField()

    def get_status_id(self, obj):
        status_name = obj.status_id
        if status_name:
            return status_name.sStatusName
        return None

    class Meta:
        model = ContractDopMS
        fields = ['amount', 'description', 'is_increase', 'dop_contr_date', 'user_id', 'status_id']


class ContractSerializer(ModelSerializer):
    """ Сериализатор для получения данных о договоре """

    Arrears = serializers.IntegerField(read_only=True)
    StudentID = StudentMSSerializer(read_only=True)
    PaymentTypeID = PaymentTypeMSSerializer(read_only=True)
    ContractStatusID = ContractStatusMSSerializer(read_only=True)
    CompanyID = CompanyMSSerializer(read_only=True)
    EduYearID = EduYearMSSerializer(read_only=True)
    SchoolID = SchoolMSSerializer(read_only=True)
    ClassID = ClassMSSerializer(read_only=True)
    DiscountID = DiscountMSSerializer(read_only=True)
    Discount = ContractDiscountMSSerializer(read_only=True)
    MonthPays = ContractMonthPayMSSerializer(read_only=True)
    ContractDop = serializers.SerializerMethodField()
    DetailContract = serializers.SerializerMethodField()

    def get_ContractDop(self, obj):
        contract_dop = ContractDopMS.objects.using('ms_sql').filter(agreement_id=obj.id)
        if len(contract_dop) == 0:
            return None
        elif len(contract_dop) == 1:
            return ContractDopMSSerializer(contract_dop.first()).data
        return ContractDopMSSerializer(contract_dop, many=True).data

    def get_DetailContract(self, obj):
        discount = DiscountMS.objects.using('ms_sql').all()
        contract_discount = ContractDiscountMS.objects.using('ms_sql').filter(ContractID=obj)
        contract_dop_sum = ContractDopMS.objects.using('ms_sql').filter(agreement_id=obj.id).aggregate(
            Sum('amount')).get('amount__sum')
        if contract_dop_sum is None:
            contract_dop_sum = 0

        contract_amount = float(obj.ContractAmount)

        for i in contract_discount:
            for j in discount.filter(id=i.DiscountID.id):
                percent = int(j.iDiscountPercent)
                contract_amount -= contract_amount * percent / 100

        contract_amount_with_discount = float(round(contract_amount, 2)) + float(contract_dop_sum)

        month_sum = contract_amount_with_discount / 9

        contract_month_pay = ContractMonthPayMS.objects.using('ms_sql').filter(ContractID=obj)
        month_pays = []

        for i in contract_month_pay:
            month_pays.append({
                'MonthAmount': str(round(month_sum, 2)),
                'MonthSum': str(round(month_sum, 2)),
                'PayDateM': i.PayDateM,
            })

        return month_pays

    class Meta:
        model = ContractMS
        fields = [
            'id', 'StudentID', 'ContractDate', 'ContractDateClose', 'ContractNum', 'ContractAmount', 'ContSum',
            'PaymentTypeID', 'ContractStatusID', 'ContractSum', 'CompanyID', 'EduYearID', 'SchoolID', 'ClassID',
            'DiscountID', 'Arrears', 'Discount', 'MonthPays', 'ContractDop', 'DetailContract'
        ]
