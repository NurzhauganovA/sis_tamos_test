from rest_framework.pagination import LimitOffsetPagination

from apps.contract.models import ContractFileUser


class ContractSearchParameterService:
    """ Сервис для работы с параметрами поиска договоров """

    @staticmethod
    def get_contract_by_student_full_name(model_obj, query_param):
        """ Получить контракты по ФИО студента """

        try:
            return model_obj.using('ms_sql').filter(StudentID__full_name__icontains=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_contract_num(model_obj, query_param):
        """ Получить контракты по номеру договора """

        try:
            return model_obj.using('ms_sql').filter(ContractNum__icontains=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_edu_year(model_obj, query_param):
        """ Получить контракты по учебному году """

        try:
            return model_obj.using('ms_sql').filter(EduYearID__EduYear__icontains=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_parent_full_name(model_obj, query_param):
        """ Получить контракты по ФИО родителя """

        try:
            return model_obj.using('ms_sql').filter(StudentID__parent__fio__icontains=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_parent_phone_number(model_obj, query_param):
        """ Получить контракты по номеру телефона родителя """

        try:
            return model_obj.using('ms_sql').filter(StudentID__parent__login__icontains=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_contract_class_num(model_obj, query_param):
        """ Получить контракты по номеру класса """

        try:
            return model_obj.using('ms_sql').filter(ClassID__class_num=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_contract_class_liter(model_obj, query_param):
        """ Получить контракты по литере класса """

        try:
            return model_obj.using('ms_sql').filter(ClassID__class_liter=query_param)
        except AttributeError:
            return model_obj

    @staticmethod
    def get_contract_by_contract_date(model_obj, query_param):
        """ Получить контракты по дате договора """

        try:
            return model_obj.using('ms_sql').filter(ContractDate__icontains=query_param)
        except AttributeError:
            return model_obj


class ContractReportService:
    """ Сервис для работы отчета по договорам """

    def __init__(self, model, serializer):
        self.model = model
        self.serializer = serializer

    def get_queryset(self):
        """ Получить queryset для отчета по договорам """

        contracts = self.model.objects.using('ms_sql').filter(ContractDate__year__gte=2023)
        signed_contracts = contracts.filter(ContractStatusID__sStatusName='Подписан')
        list_signed_contracts = [contract['ContractNum'] for contract in signed_contracts.values('ContractNum')]
        signed_with_us = ContractFileUser.objects.filter(contractNum__in=list_signed_contracts).values('contractNum')
        list_signed_with_us = [contract['contractNum'] for contract in signed_with_us]

        return signed_contracts.filter(ContractNum__in=list_signed_with_us)

    def get_contract_report(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        pagination = LimitOffsetPagination()
        pagination.default_limit = 25

        query_param_service = ContractSearchParameterService()

        student_full_name = request.query_params.get('student_full_name')
        contract_num = request.query_params.get('contract_num')
        edu_year = request.query_params.get('edu_year')
        parent_full_name = request.query_params.get('parent_full_name')
        parent_phone_number = request.query_params.get('parent_phone_number')
        contract_class_num = request.query_params.get('contract_class_num')
        contract_class_liter = request.query_params.get('contract_class_liter')
        contract_date = request.query_params.get('contract_date')

        if student_full_name:
            queryset = query_param_service.get_contract_by_student_full_name(queryset, student_full_name)
        if contract_num:
            queryset = query_param_service.get_contract_by_contract_num(queryset, contract_num)
        if edu_year:
            queryset = query_param_service.get_contract_by_edu_year(queryset, edu_year)
        if parent_full_name:
            queryset = query_param_service.get_contract_by_parent_full_name(queryset, parent_full_name)
        if parent_phone_number:
            queryset = query_param_service.get_contract_by_parent_phone_number(queryset, parent_phone_number)
        if contract_class_num:
            queryset = query_param_service.get_contract_by_contract_class_num(queryset, contract_class_num)
        if contract_class_liter:
            queryset = query_param_service.get_contract_by_contract_class_liter(queryset, contract_class_liter)
        if contract_date:
            queryset = query_param_service.get_contract_by_contract_date(queryset, contract_date)

        queryset = pagination.paginate_queryset(queryset, request)
        serializer = self.serializer(queryset, many=True)

        return pagination.get_paginated_response(serializer.data)
