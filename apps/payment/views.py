import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseBadRequest
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from apps.contract.models import ContractMS, ContractFoodMS, ContractDriverMS, TransactionMS, TransactionFoodMS, \
    TransactionDriverMS, BankMS, ClassMS
from apps.contract.services import ContractService, ContractFoodService, ContractDriverService
from apps.school.models import School, SchoolMS, Class
from apps.school.serializers import SchoolSerializer
from apps.user.models import User, UserMS


class IntegrationPaymentViewSet(ModelViewSet):
    """ Integration with Kaspi Bank """

    @staticmethod
    def get_queryset_contract(model):
        return model.objects.using('ms_sql').all()

    def get_object_contract(self, contract_num):
        if 'Д' in contract_num:
            try:
                contract = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                contract = None
        elif 'П' in contract_num:
            try:
                contract = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num)
            except ContractFoodMS.DoesNotExist:
                contract = None
        elif 'Р' in contract_num:
            try:
                contract = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num)
            except ContractDriverMS.DoesNotExist:
                contract = None
        else:
            try:
                contract = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                try:
                    contract = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num)
                except ContractFoodMS.DoesNotExist:
                    try:
                        contract = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num)
                    except ContractDriverMS.DoesNotExist:
                        contract = None

        return contract

    def get_id_of_contract(self, contract_num):
        if 'Д' in contract_num:
            try:
                contract_id = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num).id
            except ContractMS.DoesNotExist:
                contract_id = None
        elif 'П' in contract_num:
            try:
                contract_id = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num).id
            except ContractFoodMS.DoesNotExist:
                contract_id = None
        elif 'Р' in contract_num:
            try:
                contract_id = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num).id
            except ContractDriverMS.DoesNotExist:
                contract_id = None
        else:
            try:
                contract_id = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num).id
            except ContractMS.DoesNotExist:
                try:
                    contract_id = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num).id
                except ContractFoodMS.DoesNotExist:
                    try:
                        contract_id = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num).id
                    except ContractDriverMS.DoesNotExist:
                        contract_id = None

        return contract_id

    def get_transaction_object(self, contract_num):
        try:
            transaction = self.get_queryset_contract(TransactionMS).filter(agreement_id=self.get_id_of_contract(contract_num)).last().id
        except AttributeError:
            try:
                transaction = self.get_queryset_contract(TransactionFoodMS).filter(contract_id=self.get_id_of_contract(contract_num)).last().id
            except AttributeError:
                try:
                    transaction = self.get_queryset_contract(TransactionDriverMS).filter(ContractID=self.get_id_of_contract(contract_num)).last().id
                except AttributeError:
                    transaction = None

        return transaction

    def get_bin_of_school(self, contract_num):
        try:
            bin_of_school = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num).SchoolID.sBin
        except ObjectDoesNotExist:
            try:
                bin_of_school = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num).SchoolID.sBin
            except ObjectDoesNotExist:
                try:
                    bin_of_school = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num).SchoolID.sBin
                except ObjectDoesNotExist:
                    bin_of_school = None

        return bin_of_school

    def get_arrears_value_object(self, contract_num):
        try:
            arrears = ContractService(self.get_queryset_contract(ContractMS)).get_value_of_arrears(contract_num)
        except IndexError:
            try:
                arrears = ContractFoodService(self.get_queryset_contract(ContractFoodMS)).get_value_of_arrears(contract_num)
            except IndexError:
                try:
                    arrears = ContractDriverService(self.get_queryset_contract(ContractDriverMS)).get_value_of_arrears(contract_num)
                except IndexError:
                    arrears = None
        return arrears

    def check_contract_status(self, contract_num):
        try:
            status = self.get_queryset_contract(ContractMS).get(ContractNum=contract_num).ContractStatusID
        except ObjectDoesNotExist:
            try:
                status = self.get_queryset_contract(ContractFoodMS).get(ContractNum=contract_num).ContractStatusID
            except ObjectDoesNotExist:
                try:
                    status = self.get_queryset_contract(ContractDriverMS).get(ContractNum=contract_num).ContractStatusID
                except ObjectDoesNotExist:
                    status = None
        if status is not None:
            if status.sStatusName == 'Сформирован':
                result_code = 2
            elif status.sStatusName == 'Отменен':
                result_code = 3
            elif status.sStatusName == 'Расторгнут':
                result_code = 4
            elif status.sStatusName == 'Завершен':
                result_code = 5
            else:
                result_code = 0
        else:
            result_code = 1

        return result_code

    @action(['GET'], detail=False)
    def get_request_payment(self, request):
        """ Отправка запроса на оплату """

        if request.method == 'GET':
            command = request.GET.get('command')
            txn_id = request.GET.get('txn_id')
            account = request.GET.get('account')
            txn_date = request.GET.get('txn_date')
            sum_amount = request.GET.get('sum')

            try:
                self.get_object_contract(account)
                if self.get_object_contract(account) is None:
                    result_code = 1
                result_code = 0
            except ObjectDoesNotExist:
                result_code = 1
            except AttributeError:
                result_code = 1
            except ValueError:
                result_code = 1

            if command == 'check':
                try:
                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": "",
                        "fields": {
                            "Номер договора": {
                                "value": account
                            },
                            "BIN школы": {
                                "value": self.get_bin_of_school(account)
                            },
                            "ФИО ребенка": {
                                "value": self.get_object_contract(account).StudentID.full_name
                            },
                            "Класс/группа": {
                                "value": f'{self.get_object_contract(account).ClassID.class_num}{self.get_object_contract(account).ClassID.class_liter}'
                            },
                            "Вид оплаты": {
                                "value": "Оплата по договору"
                            },
                            "Задолженность по договору": {
                                "value": self.get_arrears_value_object(account) or 0
                            }
                        }
                    }
                except AttributeError:
                    result_code = 1

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": "",
                    }

                except IndexError:
                    result_code = 1

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": "",
                    }

                if self.check_contract_status(account) == 2:
                    result_code = 2

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": 'Контракт еще не доступен!',
                    }

                elif self.check_contract_status(account) == 3:
                    result_code = 3

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": 'Контракт имеет статус "Отменен"',
                    }

                elif self.check_contract_status(account) == 4:
                    result_code = 4

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": 'Контракт имеет статус "Расторгнут"',
                    }

                elif self.check_contract_status(account) == 5:
                    result_code = 5

                    response_data = {
                        "txn_id": txn_id,
                        "result": result_code,
                        "comment": 'Контракт имеет статус "Завершен"',
                    }

                return JsonResponse(response_data)

            elif command == 'pay':
                try:
                    get_object = self.get_object_contract(account)
                    if get_object is None:
                        result_code = 1

                        response_data = {
                            "txn_id": txn_id,
                            "result": result_code,
                            "comment": "",
                        }

                        return JsonResponse(response_data)

                except ObjectDoesNotExist:
                    result_code = 1
                except AttributeError:
                    result_code = 1
                except ValueError:
                    result_code = 1

                result_code = 0
                date_now = datetime.datetime.now()
                try:
                    user = User.objects.get(id=request.user.id).login.split('+7')[1]
                except User.DoesNotExist:
                    user = None

                TransactionMS.objects.using('ms_sql').create(
                    agreement_id=ContractMS.objects.using('ms_sql').get(ContractNum=account),
                    amount=sum_amount,
                    description='test',
                    is_increase=True,
                    payment_type=ContractMS.objects.using('ms_sql').get(ContractNum=account).PaymentTypeID,
                    user_id=UserMS.objects.using('ms_sql').filter(login=user).first() or None,
                    name='От родителей',
                    contribution=0,
                    trans_date=date_now,
                    bank_id=BankMS.objects.using('ms_sql').get(name='KASPI'),
                    is_dop_contr=False,
                    dop_contr_date=None
                )

                response_data = {
                    "txn_id": txn_id,
                    "prv_txn_id": self.get_transaction_object(account),
                    "result": result_code,
                    "sum": sum_amount,
                    "comment": "OK"
                }
                return JsonResponse(response_data)

        return HttpResponseBadRequest()


class Migration(ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def create(self, request, *args, **kwargs):
        school_ms = SchoolMS.objects.using('ms_sql').all()
        class_ms = ClassMS.objects.using('ms_sql').all()

        # for school in school_ms:
        #     School.objects.create(
        #         sSchool_name=school.sSchool_name,
        #         sSchool_address=school.sSchool_address,
        #         sSchool_direct=school.sSchool_direct,
        #         sSchool_language=school.sSchool_language,
        #         isSchool=school.isSchool,
        #         sCommentary=school.sCommentary,
        #         sBin=school.sBin
        #     )

        for class_ in class_ms:
            Class.objects.create(
                school=School.objects.get(id=class_.school_id.id),
                class_num=class_.class_num,
                class_liter=class_.class_liter,
                commentary=class_.commentary,
                isActive=class_.isActive,
                teacher=None,
                isGraduated=False,
                max_class_num=11,
                modified=datetime.datetime.now()
            )

        return JsonResponse({'message': 'Школы успешно перенесены!'})
