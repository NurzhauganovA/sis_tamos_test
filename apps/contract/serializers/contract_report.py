from rest_framework import serializers
from apps.contract.models import ContractMS, ContractMonthPayMS, TransactionMS, DiscountMS


class DiscountMSSerializer(serializers.ModelSerializer):
    """ Сериализатор для скидок """

    DiscountName = serializers.SerializerMethodField()
    DiscountType = serializers.SerializerMethodField()
    DiscountAmount = serializers.SerializerMethodField()
    DiscountDate = serializers.SerializerMethodField()

    @staticmethod
    def get_DiscountName(obj):
        try:
            return obj.sDiscountName
        except AttributeError:
            return None

    @staticmethod
    def get_DiscountType(obj):
        try:
            return obj.iDiscountType.sDiscountType
        except AttributeError:
            return None

    @staticmethod
    def get_DiscountAmount(obj):
        try:
            return obj.iDiscountPercent
        except AttributeError:
            return None

    @staticmethod
    def get_DiscountDate(obj):
        return None

    class Meta:
        model = DiscountMS
        fields = ('id', 'DiscountName', 'DiscountType', 'DiscountAmount', 'DiscountDate')


class ContractListReportSerializer(serializers.ModelSerializer):
    """ Сериализатор для списка договоров с задолженностью """

    ParentFullName = serializers.SerializerMethodField()
    StudentFullName = serializers.SerializerMethodField()
    SumContract = serializers.SerializerMethodField()
    ContractStatus = serializers.SerializerMethodField()
    PaymentPeriod = serializers.SerializerMethodField()
    SumContractDiscount = serializers.SerializerMethodField()
    EduYear = serializers.SerializerMethodField()
    SchoolName = serializers.SerializerMethodField()
    Class = serializers.SerializerMethodField()
    DiscountID = serializers.SerializerMethodField()
    ContributionSum = serializers.SerializerMethodField()
    ArrearsSum = serializers.SerializerMethodField()

    @staticmethod
    def get_ParentFullName(obj):
        try:
            return obj.StudentID.parent_id.full_name
        except AttributeError:
            return None

    @staticmethod
    def get_StudentFullName(obj):
        try:
            return obj.StudentID.full_name
        except AttributeError:
            return None

    @staticmethod
    def get_SumContract(obj):
        return obj.ContractAmount

    @staticmethod
    def get_ContractStatus(obj):
        try:
            return obj.ContractStatusID.sStatusName
        except AttributeError:
            return None

    @staticmethod
    def get_PaymentPeriod(obj):
        try:
            return obj.PaymentTypeID.sPaymentType
        except AttributeError:
            return None

    @staticmethod
    def get_SumContractDiscount(obj):
        return obj.ContractSum

    @staticmethod
    def get_EduYear(obj):
        try:
            return obj.EduYearID.sEduYear
        except AttributeError:
            return None

    @staticmethod
    def get_SchoolName(obj):
        try:
            return obj.SchoolID.sSchool_name
        except AttributeError:
            return None

    @staticmethod
    def get_Class(obj):
        try:
            class_num = obj.ClassID.class_num
            class_liter = obj.ClassID.class_liter
            return f'{class_num} {class_liter}'
        except AttributeError:
            return None

    @staticmethod
    def get_DiscountID(obj):
        try:
            discounts = DiscountMS.objects.using('ms_sql').filter(id=obj.DiscountID.id)
            return DiscountMSSerializer(discounts, many=True).data
        except AttributeError:
            return None
        except DiscountMS.DoesNotExist:
            return None

    @staticmethod
    def get_ContributionSum(obj):
        try:
            return obj.ContSum
        except AttributeError:
            return None

    @staticmethod
    def get_ArrearsSum(obj):
        pays = ContractMonthPayMS.objects.using('ms_sql').filter(ContractID=obj.id)
        transactions = TransactionMS.objects.using('ms_sql').filter(agreement_id=obj.id)

        pays_sum = 0
        transactions_sum = 0
        for pay in pays:
            try:
                pays_sum += pay.MonthSum
            except TypeError:
                pays_sum += int(pay.MonthSum)
        for transaction in transactions:
            try:
                transactions_sum += transaction.amount
            except TypeError:
                transactions_sum += int(transaction.amount)

        try:
            result = int(pays_sum) - int(transactions_sum)
        except TypeError:
            result = pays_sum - transactions_sum

        return result if result > 0 else 0

    class Meta:
        model = ContractMS
        fields = ('id', 'ParentFullName', 'StudentFullName', 'ContractDate', 'ContractDateClose', 'ContractNum', 'SumContract',
                  'ContractStatus', 'PaymentPeriod', 'SumContractDiscount', 'EduYear', 'Contribution',
                  'ContributionSum', 'SchoolName', 'Class', 'DiscountID', 'ArrearsSum')
