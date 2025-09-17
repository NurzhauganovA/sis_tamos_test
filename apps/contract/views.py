import base64
import hashlib
import uuid
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .contract_signature_service import ContractSignatureService
from .models import ContractMS, ContractDopMS, ContractFoodMS, ContractDriverMS, RawContractTemplate, \
    MarkedUpContractTemplate, ContractSignature, ContractFileUser
from .serializers.contract import ContractSerializer, ContractDopMSSerializer
from .serializers.contract_driver import ContractDriverSerializer
from .serializers.contract_food import ContractFoodSerializer
from .serializers.contract_report import ContractListReportSerializer
from .serializers.contract_sign import SignContractWithEDSSerializer, CreateSignContractWithEDSSerializer, \
    ContractSignatureSerializer, ContractSignatureCreateSerializer, ContractFileUserSerializer
from .serializers.contract_templates import (
    RawContractTemplateSerializer,
    MarkedUpContractTemplateSerializer,
    RawContractTemplateForMarkUpSerializer
)

from .services import ContractService, ContractDownloadService, ContractFoodService, ContractDriverService
from .services_eds import SignContractWithEDSService
from .services_report import ContractReportService

from rest_framework import permissions


class Contract(ModelViewSet):
    """
        API для работы с договорами студентов.
        Данные контрактов хранятся в MS SQL.
        Пока что только GET запросы, т.к. в MS SQL у нас нет возможности создавать записи.
    """

    queryset = ContractMS.objects.using('ms_sql').filter(ContractDate__year__gt=2019)
    serializer_class = ContractSerializer
    http_method_names = ['get', 'post']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract_service = ContractService(self.queryset)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """ Получение данных договора по id студента """

        contract = self.contract_service.get_contract(student_id=pk)
        return contract

    @action(methods=['get'], detail=True, serializer_class=ContractDopMSSerializer)
    def contract_dop(self, request, *args, **kwargs):
        """ Получение данных о дополнительных договорах """

        contract_dop = ContractDopMS.objects.using('ms_sql').filter(agreement_id=kwargs['pk']).last().agreement_id
        if contract_dop is None:
            return Response({'error': 'Дополнительный договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        try:
            contract = ContractMS.objects.using('ms_sql').get(id=contract_dop.id)
        except ContractMS.DoesNotExist:
            return Response({'error': 'Дополнительный договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        main_contract = ContractSerializer(contract).data

        return Response(main_contract)

    @action(methods=['get'], detail=True)
    def contract_dop_download(self, request, *args, **kwargs):
        """ Скачать дополнительный договор """

        contract_dop = ContractDopMS.objects.using('ms_sql').filter(agreement_id=kwargs['pk']).last().agreement_id

        if contract_dop is None:
            return Response({'error': 'Дополнительный договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        # if contract_dop.ContractDate.year < datetime.now().year - 1:
        #     return Response({'error': 'Скачать договор можно только на текущий год'}, status=status.HTTP_403_FORBIDDEN)

        contract_download_service = ContractDownloadService(contract_dop)
        contract_dop = contract_download_service.contract_download(request, contract_num=contract_dop.ContractNum, is_dop_contract=True)

        return contract_dop

    @action(methods=['get'], detail=True)
    def contract_dop_get_data(self, request, *args, **kwargs):
        """ Получение данных для подписи дополнительного договора """

        contract_dop = ContractDopMS.objects.using('ms_sql').filter(agreement_id=kwargs['pk']).last().agreement_id

        if contract_dop is None:
            return Response({'error': 'Дополнительный договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        contract_sign_service = SignContractWithEDSService(contract_dop)
        contract_get_data = contract_sign_service.check_data_user_certificate(request, contract_dop)

        return contract_get_data

    @action(methods=['post'], detail=True)
    def contract_dop_sign_eds(self, request, *args, **kwargs):
        """ Подпись дополнительного договора с помощью ЭЦП """

        contract_dop = ContractDopMS.objects.using('ms_sql').filter(agreement_id=kwargs['pk']).last().agreement_id

        if contract_dop is None:
            return Response({'error': 'Дополнительный договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        # if contract_dop.ContractDate.year < datetime.now().year - 1:
        #     return Response({'error': 'Подписать договор можно только на текущий год'}, status=status.HTTP_403_FORBIDDEN)

        contract_sign_service = SignContractWithEDSService(contract_dop)
        contract_sign = contract_sign_service.sign_contract_document(request, contract_dop, is_dop_contract=True)

        return contract_sign


class ContractFood(ModelViewSet):
    """
        API для работы с договорами студентов касаемо питании.
        Данные контрактов хранятся в MS SQL.
        Пока что только GET запросы, т.к. в MS SQL у нас нет возможности создавать записи.
    """

    queryset = ContractFoodMS.objects.using('ms_sql').filter(ContractDate__year__gt=2021)
    serializer_class = ContractFoodSerializer
    http_method_names = ['get']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract_food_service = ContractFoodService(self.queryset)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """ Получение данных договора по id студента """

        contract_student = self.contract_food_service.get_contract_food(student_id=pk)
        return contract_student


class ContractDriver(ModelViewSet):
    """
        API для работы с договорами студентов касаемо развозки.
        Данные контрактов хранятся в MS SQL.
        Пока что только GET запросы, т.к. в MS SQL у нас нет возможности создавать записи.
    """

    queryset = ContractDriverMS.objects.using('ms_sql').filter(ContractDate__year__gt=2021)
    serializer_class = ContractDriverSerializer
    http_method_names = ['get']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract_driver_service = ContractDriverService(self.queryset)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """ Получение данных договора по id студента """

        contract_student = self.contract_driver_service.get_contract_driver(student_id=pk)
        return contract_student


class ContractDownload(ModelViewSet):
    """
        API для скачивания договоров студентов.
    """

    serializer_class = ContractSerializer
    http_method_names = ['get']

    def get_object(self):
        contract_num = str(self.kwargs.get('pk'))
        is_dop_contract = False

        # Проверка, является ли контракт дополнительным договором
        if contract_num.count('-') == 2 and contract_num.endswith('Д'):
            parts = contract_num.rsplit('-', 1)
            contract_num = parts[0] + '/' + parts[1]
            is_dop_contract = True

        if 'Д' in contract_num:
            try:
                print("Fetching contract with 'Д' in contract_num")
                contracts = ContractMS.objects.using('ms_sql').all()
                print("Length of contracts:", len(contracts))
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
                print(f"Found contract: {contract}")
            except ContractMS.DoesNotExist:
                contract = None
        elif 'П' in contract_num:
            try:
                contract = ContractFoodMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractFoodMS.DoesNotExist:
                contract = None
        elif 'Р' in contract_num:
            try:
                contract = ContractDriverMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractDriverMS.DoesNotExist:
                contract = None
        else:
            try:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                contract = ContractFoodMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractFoodMS.DoesNotExist:
                contract = ContractDriverMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractDriverMS.DoesNotExist:
                contract = None

        self.contract_download_service = ContractDownloadService(contract)

        return contract, is_dop_contract

    @action(methods=['get'], detail=True)
    def contract_download(self, request, *args, **kwargs):
        """ Скачивание договора по номеру договора """

        try:
            selected_contract, is_dop_contract = self.get_object()
            print(f"Selected contract: {selected_contract}, is_dop_contract: {is_dop_contract}")
            contract_num = self.contract_download_service.contract_download(
                request, contract_num=selected_contract.ContractNum, is_dop_contract=is_dop_contract
            )
        except ValueError as e:
            return JsonResponse({'error': e}, status=status.HTTP_403_FORBIDDEN)

        return contract_num


class SignContractWithEDS(ModelViewSet):
    """
    Подпись договора с помощью ЭЦП
    Генерировать QR-код с данными подписи
    Использовать логику из документации ncanode.kz
    """

    serializer_class = SignContractWithEDSSerializer
    http_method_names = ['get', 'post']

    def get_contract_ms(self):
        pk = self.kwargs.get('pk')
        return ContractMS.objects.using('ms_sql').get(ContractNum=pk)

    def get_contract_food_ms(self):
        pk = self.kwargs.get('pk')
        return ContractFoodMS.objects.using('ms_sql').get(ContractNum=pk)

    def get_contract_driver_ms(self):
        pk = self.kwargs.get('pk')
        return ContractDriverMS.objects.using('ms_sql').get(ContractNum=pk)

    def get_object(self):
        contract_num = str(self.kwargs.get('pk'))
        if 'Д' in contract_num:
            contract = self.get_contract_ms()
        elif 'П' in contract_num:
            contract = self.get_contract_food_ms()
        elif 'Р' in contract_num:
            contract = self.get_contract_driver_ms()
        else:
            try:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                contract = ContractFoodMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractFoodMS.DoesNotExist:
                contract = ContractDriverMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractDriverMS.DoesNotExist:
                contract = None

        self.sign_contract_with_eds_service = SignContractWithEDSService(contract)

        return contract

    @action(methods=['post'], detail=True, serializer_class=SignContractWithEDSSerializer)
    def sign_contract_get_data(self, request, *args, **kwargs):
        """ Получение данных для подписи договора """

        try:
            selected_contract = self.get_object()

            # if selected_contract.ContractDate.year < datetime.now().year - 1:
            #     return Response({'error': 'Подписать договор можно только на текущий год'}, status=status.HTTP_403_FORBIDDEN)

            contract_data = self.sign_contract_with_eds_service.check_data_user_certificate(request, selected_contract)
        except ObjectDoesNotExist:
            return Response({'error': 'Договор не найден'}, status=status.HTTP_403_FORBIDDEN)

        return contract_data

    @action(methods=['post'], detail=True, serializer_class=CreateSignContractWithEDSSerializer)
    def sign_contract_with_eds(self, request, *args, **kwargs):
        """ Подпись договора с помощью ЭЦП """

        try:
            selected_contract = self.get_object()

            # if selected_contract.ContractDate.year < datetime.now().year - 1:
            #     return Response({'error': 'Подписать договор можно только на текущий год'}, status=status.HTTP_403_FORBIDDEN)

            contract = self.sign_contract_with_eds_service.sign_contract_document(request, selected_contract, is_dop_contract=False)
        except ObjectDoesNotExist:
            print('Договор не найден')
            return Response({'error': 'Договор не найден!'}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            print(f'ValueError: {e}')
            return Response({'error': e}, status=status.HTTP_403_FORBIDDEN)

        return contract


class RawContractTemplateView(ModelViewSet):
    """API для работы с сырыми шаблонами (без переменных)."""

    serializer_class = RawContractTemplateSerializer
    queryset = RawContractTemplate.objects.all()

    @action(
        methods=['get'],
        detail=True,
        url_path='template-for-markup',
        url_name='template for mark up',
        serializer_class=RawContractTemplateForMarkUpSerializer,
    )
    def get_template_with_variables(self, request, *args, **kwargs):
        """Получение сырого документа с возможными переменными."""
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)


class MarkedUpContractTemplateView(ModelViewSet):
    """API для работы с размеченными шаблонами."""

    serializer_class = MarkedUpContractTemplateSerializer
    queryset = MarkedUpContractTemplate.objects.all()


class ContractListReportView(ModelViewSet):
    """ API для работы с отчетами """

    serializer_class = ContractListReportSerializer
    http_method_names = ['get']
    permission_classes = [permissions.AllowAny]
    contract_list_service = ContractReportService(ContractMS, ContractListReportSerializer)

    @action(methods=['get'], detail=False, permission_classes=[permissions.AllowAny])
    def contract_list_report(self, request, *args, **kwargs):
        """ Получение данных для отчета """

        contract_list = self.contract_list_service.get_contract_report(request=request, *args, **kwargs)
        return contract_list


class ContractSigningView(APIView):
    """API для подписания контрактов"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Обрабатывает подписание контракта

        Expected JSON:
        {
            "contract_num": "2024Д-1400",
            "cms": "base64_cms_signature",
            "data": "base64_signed_data"
        }
        """
        try:
            contract_num = request.data.get('contract_num')
            cms_signature = request.data.get('cms')
            signed_data = request.data.get('data')
            is_dop_contract = request.data.get('is_dop_contract', False)

            if not all([contract_num, cms_signature, signed_data]):
                return Response({
                    'success': False,
                    'error': 'Отсутствуют обязательные параметры: contract_num, cms, data',
                    'error_code': 'MISSING_PARAMETERS'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not is_dop_contract:
                is_dop_contract = self._is_additional_contract(contract_num)

            # Находим контракт по номеру
            try:
                if is_dop_contract:
                    contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                        agreement_id__ContractNum=contract_num
                    ).first()
                    if not contract_dop:
                        return Response({
                            'success': False,
                            'error': 'Дополнительный договор не найден',
                            'error_code': 'CONTRACT_NOT_FOUND'
                        }, status=status.HTTP_404_NOT_FOUND)
                    contract = contract_dop.agreement_id
                else:
                    contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Контракт не найден',
                    'error_code': 'CONTRACT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)

            # Проверяем статус контракта
            # if is_dop_contract:
            #     contract_dop = ContractDopMS.objects.using('ms_sql').filter(
            #         agreement_id__ContractNum=contract_num
            #     ).first()
            #     if contract_dop.status_id.sStatusName != 'На рассмотрении':
            #         return Response({
            #             'success': False,
            #             'error': 'Дополнительный договор должен быть в статусе "На рассмотрении"',
            #             'error_code': 'INVALID_STATUS'
            #         }, status=status.HTTP_400_BAD_REQUEST)
            # else:
            #     if contract.ContractStatusID.sStatusName != 'На рассмотрении':
            #         return Response({
            #             'success': False,
            #             'error': 'Контракт должен быть в статусе "На рассмотрении"',
            #             'error_code': 'INVALID_STATUS'
            #         }, status=status.HTTP_400_BAD_REQUEST)

            service = ContractSignatureService()
            result = service.verify_and_save_signature(
                contract_num=contract_num,
                cms_signature=cms_signature,
                signed_data=signed_data,
                user=request.user,
                is_dop_contract=is_dop_contract
            )

            if result['success']:
                # Дополнительная проверка ИИН если нужно
                user_iin = getattr(request.user.user_info, 'iin', None)  # Предполагаем что у User есть поле iin
                signer_iin = result.get('signer_iin')

                if user_iin and signer_iin and user_iin != signer_iin:
                    ContractSignature.objects.filter(signature_uid=result.get('signature_uid')).delete()

                    return Response({
                        'success': False,
                        'error': 'ИИН подписанта не совпадает с ИИН пользователя',
                        'error_code': 'IIN_MISMATCH'
                    }, status=status.HTTP_403_FORBIDDEN)

                return Response(result, status=status.HTTP_200_OK)
            else:
                http_status = status.HTTP_400_BAD_REQUEST
                if result.get('error_code') == 'CONTRACT_NOT_FOUND':
                    http_status = status.HTTP_404_NOT_FOUND
                elif result.get('error_code') in ['VERIFICATION_FAILED', 'TIMEOUT']:
                    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

                return Response(result, status=http_status)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _is_additional_contract(self, contract_num: str) -> bool:
        """Проверяет, является ли контракт дополнительным договором по его номеру"""
        return ContractDopMS.objects.using('ms_sql').filter(agreement_id__ContractNum=contract_num).exists()


class ContractSignaturesView(APIView):
    """API для получения подписей контракта"""

    permission_classes = [IsAuthenticated]

    def get(self, request, contract_num):
        """Получает все подписи для контракта по его ID"""

        try:
            # Используем сервис для получения подписей
            service = ContractSignatureService()
            result = service.get_contract_signatures(contract_num)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                error_code = result.get('error_code', 'UNKNOWN_ERROR')
                http_status = status.HTTP_404_NOT_FOUND if error_code == 'CONTRACT_NOT_FOUND' else status.HTTP_400_BAD_REQUEST
                return Response(result, status=http_status)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Ошибка при получении подписей: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SignatureValidityView(APIView):
    """API для проверки валидности подписи"""

    permission_classes = [IsAuthenticated]

    def get(self, request, signature_uid):
        """Проверяет валидность конкретной подписи"""

        try:
            if not signature_uid:
                return Response({
                    'success': False,
                    'error': 'Не указан signature_uid',
                    'error_code': 'MISSING_SIGNATURE_UID'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Используем сервис для проверки подписи
            service = ContractSignatureService()
            result = service.check_signature_validity(signature_uid)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                error_code = result.get('error_code', 'UNKNOWN_ERROR')
                http_status = status.HTTP_404_NOT_FOUND if error_code == 'SIGNATURE_NOT_FOUND' else status.HTTP_400_BAD_REQUEST
                return Response(result, status=http_status)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Ошибка при проверке подписи: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContractSigningDataView(APIView):
    """API для получения данных контракта для подписания"""

    permission_classes = [IsAuthenticated]

    def get(self, request, contract_num):
        """
        Получает данные контракта которые нужно подписать

        Returns:
        {
            "contract_num": "2024Д-1400",
            "data": "base64_contract_data",
            "hash": "sha256_hash",
            "contract_info": {...}
        }
        """
        try:
            is_dop_contract = self._is_additional_contract(contract_num)

            # Находим контракт
            try:
                if is_dop_contract:
                    contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                        agreement_id__ContractNum=contract_num
                    ).first()
                    if not contract_dop:
                        return Response({
                            'success': False,
                            'error': 'Дополнительный договор не найден',
                            'error_code': 'CONTRACT_NOT_FOUND'
                        }, status=status.HTTP_404_NOT_FOUND)
                    contract = contract_dop.agreement_id
                else:
                    contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Контракт не найден',
                    'error_code': 'CONTRACT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)

            # Формируем данные для подписания
            contract_data = self._prepare_contract_data(contract, is_dop_contract)

            # Кодируем в base64
            contract_data_base64 = base64.b64encode(contract_data.encode('utf-8')).decode('utf-8')

            # Вычисляем хэш
            contract_hash = hashlib.sha256(contract_data.encode('utf-8')).hexdigest()

            # Информация о контракте
            contract_info = {
                'contract_num': contract.ContractNum,
                'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract, 'StudentID') and contract.StudentID else '',
                'is_dop_contract': is_dop_contract
            }

            if is_dop_contract:
                contract_info['contract_type'] = 'Дополнительный договор'
                # Добавляем информацию о дополнительном договоре
                contract_info['dop_amount'] = str(contract_dop.amount) if contract_dop.amount else ''
                contract_info['description'] = contract_dop.description or ''

            return Response({
                'success': True,
                'contract_num': contract_num,
                'data': contract_data_base64,
                'hash': contract_hash,
                'contract_info': contract_info,
                'is_dop_contract': is_dop_contract
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Ошибка при получении данных контракта: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _prepare_contract_data(self, contract, is_dop_contract=False):
        """Подготавливает данные контракта для подписания"""
        contract_type = "DOP_CONTRACT" if is_dop_contract else "MAIN_CONTRACT"
        # Формируем строку с ключевыми данными контракта
        contract_data = (
            f"CONTRACT_SIGN:{contract_type}:{contract.ContractNum}:"
            f"{contract.ContractAmount}:"
            f"{contract.ContractDate}:"
            f"{getattr(contract, 'StudentID_id', '')}:"
            f"{getattr(contract, 'ContractStatusID_id', '')}"
        )
        return contract_data

    def _is_additional_contract(self, contract_num: str) -> bool:
        """Проверяет, является ли контракт дополнительным договором по его номеру"""
        return ContractDopMS.objects.using('ms_sql').filter(agreement_id__ContractNum=contract_num).exists()


class SignatureVerificationView(APIView):
    """API для проверки подписи по QR-коду"""

    permission_classes = [permissions.AllowAny]  # Публичный доступ для проверки

    def get(self, request, signature_uid):
        """
        Получает информацию о подписи для отображения на фронтенде

        Returns:
        {
            "success": true,
            "signature_info": {
                "signature_uid": "uuid",
                "contract_num": "2024Д-1400",
                "signer_iin": "123456789012",
                "signed_at": "2024-01-15T10:30:00Z",
                "is_valid": true,
                "contract_info": {
                    "student_name": "Иванов Иван Иванович",
                    "contract_amount": "500000",
                    "contract_date": "2024-01-10"
                },
                "certificate_info": {
                    "common_name": "ИВАНОВ ИВАН ИВАНОВИЧ",
                    "serial_number": "123456789",
                    "valid_from": "2023-01-01",
                    "valid_to": "2025-01-01"
                }
            }
        }
        """
        try:
            # Находим подпись
            try:
                signature = ContractSignature.objects.get(signature_uid=signature_uid)
            except ContractSignature.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Подпись не найдена',
                    'error_code': 'SIGNATURE_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)

            is_dop_contract = self._is_additional_contract(signature.contract_num)

            # Получаем информацию о контракте
            try:
                if is_dop_contract:
                    contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                        agreement_id__ContractNum=signature.contract_num
                    ).first()
                    if contract_dop:
                        contract = contract_dop.agreement_id
                        contract_info = {
                            'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract,
                                                                                                    'StudentID') and contract.StudentID else '',
                            'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                            'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                            'contract_status': getattr(contract.ContractStatusID, 'sStatusName', '') if hasattr(
                                contract, 'ContractStatusID') and contract.ContractStatusID else '',
                            'contract_type': 'Дополнительный договор',
                            'dop_amount': str(contract_dop.amount) if contract_dop.amount else '',
                            'description': contract_dop.description or ''
                        }
                    else:
                        contract_info = self._get_default_contract_info()
                else:
                    contract = ContractMS.objects.using('ms_sql').get(ContractNum=signature.contract_num)
                    contract_info = {
                        'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract,
                                                                                                'StudentID') and contract.StudentID else '',
                        'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                        'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                        'contract_status': getattr(contract.ContractStatusID, 'sStatusName', '') if hasattr(contract,
                                                                                                            'ContractStatusID') and contract.ContractStatusID else '',
                        'contract_type': 'Основной договор'
                    }
            except ContractMS.DoesNotExist:
                contract_info = self._get_default_contract_info()

            # Проверяем актуальность подписи
            is_document_modified = signature.is_document_modified
            if is_document_modified and signature.is_valid:
                signature.is_valid = False
                signature.save()

            signer_type = self._determine_signer_type(signature)

            # Формируем ответ
            signature_info = {
                'signature_uid': str(signature.signature_uid),
                'contract_num': signature.contract_num,
                'signer_iin': signature.signer_iin,
                'signer_type': signer_type,
                'signed_at': signature.signed_at.isoformat(),
                'is_valid': signature.is_valid,
                'is_document_modified': is_document_modified,
                'contract_info': contract_info,
                'certificate_info': signature.certificate_info,
                'verification_status': self._get_verification_status(signature, is_document_modified)
            }

            return Response({
                'success': True,
                'signature_info': signature_info
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Ошибка при проверке подписи: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _is_additional_contract(self, contract_num: str) -> bool:
        """Проверяет, является ли контракт дополнительным договором по его номеру"""
        return ContractDopMS.objects.using('ms_sql').filter(agreement_id__ContractNum=contract_num).exists()

    def _get_default_contract_info(self):
        """Возвращает дефолтную информацию о контракте, если контракт не найден"""
        return {
            'student_name': 'Информация недоступна',
            'contract_amount': '',
            'contract_date': '',
            'contract_status': '',
            'contract_type': 'Неизвестно'
        }

    def _determine_signer_type(self, signature):
        if signature.created_by is None:
            return 'director'
        return 'parent'

    def _get_verification_status(self, signature, is_document_modified):
        """Определяет статус верификации подписи"""
        if not signature.is_valid:
            if is_document_modified:
                return {
                    'status': 'invalid',
                    'message': 'Подпись недействительна: документ был изменен после подписания',
                    'color': 'red'
                }
            else:
                return {
                    'status': 'invalid',
                    'message': 'Подпись недействительна',
                    'color': 'red'
                }
        else:
            return {
                'status': 'valid',
                'message': 'Подпись действительна',
                'color': 'green'
            }


@method_decorator(csrf_exempt, name='dispatch')
class ContractSigningWebView(View):
    """Веб-интерфейс для подписания контрактов (для тестирования)"""

    def get(self, request, contract_num):
        """Отображает страницу для подписания контракта"""

        try:
            contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)

            html_content = f"""
            <!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Подписание контракта {contract.ContractNum}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .contract-info {{ background: #f5f5f5; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
                    .button:hover {{ background: #0056b3; }}
                    .error {{ color: red; margin: 10px 0; }}
                    .success {{ color: green; margin: 10px 0; }}
                    #log {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; max-height: 300px; overflow-y: auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Подписание контракта</h1>

                    <div class="contract-info">
                        <h3>Информация о контракте:</h3>
                        <p><strong>Номер:</strong> {contract.ContractNum}</p>
                        <p><strong>Студент:</strong> {contract.StudentID.full_name if contract.StudentID else 'Не указан'}</p>
                        <p><strong>Сумма:</strong> {contract.ContractAmount if contract.ContractAmount else 'Не указана'}</p>
                        <p><strong>Дата:</strong> {contract.ContractDate if contract.ContractDate else 'Не указана'}</p>
                        <p><strong>Статус подписи:</strong> <span id="signature-status">{contract.signature_status}</span></p>
                    </div>

                    <button class="button" onclick="signContract()">Подписать через NCALayer</button>
                    <button class="button" onclick="checkSignatures()" style="background: #28a745;">Проверить подписи</button>

                    <div id="message"></div>
                    <div id="log"></div>
                    <div id="signatures"></div>
                </div>

                <script>
                    const CONTRACT_NUM = '{contract.ContractNum}';
                    const TEST_MODE = false;
                    const NCA_LAYER_URL = 'wss://127.0.0.1:13579/';

                    function log(message) {{
                        const logDiv = document.getElementById('log');
                        logDiv.innerHTML += new Date().toLocaleTimeString() + ': ' + message + '<br>';
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }}

                    async function signContract() {{
                        try {{
                            log('Получение данных для подписания...');

                            // Получаем данные для подписания
                            const dataResponse = await fetch(`/api/v1/contract/contracts/${{CONTRACT_NUM}}/signing-data/`);
                            const dataResult = await dataResponse.json();

                            if (!dataResult.success) {{
                                throw new Error(dataResult.error);
                            }}

                            const dataToSign = dataResult.data_to_sign;
                            log('Данные для подписания получены: ' + dataToSign.substring(0, 50) + '...');

                            // Подключаемся к NCALayer
                            log('Подключение к NCALayer...');
                            const socket = new WebSocket(NCA_LAYER_URL);

                            socket.onopen = () => {{
                                log('Соединение с NCALayer установлено');

                                let message = null;
                                if (TEST_MODE) {{
                                    message = {{
                                        "module": "kz.gov.pki.knca.commonUtils",
                                        "method": "createCMSSignatureFromBase64",
                                        "args": ["PKCS12", "SIGNATURE", dataToSign, false]
                                    }};
                                }} else {{
                                    message = {{
                                        "args": {{
                                            "format": "cms",
                                            "locale": "ru",
                                            "data": dataToSign,
                                            "signingParams": {{
                                                "decode": true,
                                                "encapsulate": false,
                                                "digested": false,
                                                "tsaProfile": {{}}
                                            }},
                                            "signerParams": {{
                                                "extKeyUsageOids": ["1.3.6.1.5.5.7.3.2"]
                                            }}
                                        }},
                                        "module": "kz.gov.pki.knca.basics",
                                        "method": "sign"
                                    }};
                                }}

                                socket.send(JSON.stringify(message));
                                log('Команда подписания отправлена в NCALayer');
                            }};

                            socket.onmessage = async (event) => {{
                                const message = JSON.parse(event.data);
                                log('Ответ от NCALayer получен');

                                let cms = '';
                                if (TEST_MODE) {{
                                    cms = message.responseObject;
                                }} else {{
                                    cms = message.body?.result?.[0];
                                }}

                                if (cms) {{
                                    log('Подпись получена, отправка на сервер...');

                                    // Отправляем подпись на сервер Django
                                    const signResponse = await fetch('/api/v1/contract/contracts/sign/', {{
                                        method: 'POST',
                                        headers: {{
                                            'Content-Type': 'application/json',
                                            'X-CSRFToken': getCookie('csrftoken')
                                        }},
                                        body: JSON.stringify({{
                                            contract_num: CONTRACT_NUM,
                                            cms: cms,
                                            data: dataToSign
                                        }})
                                    }});

                                    const signResult = await signResponse.json();

                                    if (signResult.success) {{
                                        document.getElementById('message').innerHTML = '<div class="success">Контракт успешно подписан!</div>';
                                        document.getElementById('signature-status').textContent = 'signed';
                                        log('Подпись успешно сохранена');
                                        checkSignatures();
                                    }} else {{
                                        document.getElementById('message').innerHTML = '<div class="error">Ошибка: ' + signResult.error + '</div>';
                                        log('Ошибка: ' + signResult.error);
                                    }}
                                }} else if (message.errorCode) {{
                                    throw new Error('Ошибка NCALayer: ' + message.errorMessage);
                                }}

                                socket.close();
                            }};

                            socket.onerror = () => {{
                                throw new Error('Ошибка соединения с NCALayer');
                            }};

                        }} catch (error) {{
                            document.getElementById('message').innerHTML = '<div class="error">Ошибка: ' + error.message + '</div>';
                            log('Ошибка: ' + error.message);
                        }}
                    }}

                    async function checkSignatures() {{
                        try {{
                            log('Получение списка подписей...');

                            const response = await fetch(`/api/v1/contract/contracts/${{CONTRACT_NUM}}/signatures/`);
                            const result = await response.json();

                            if (result.success) {{
                                const signaturesDiv = document.getElementById('signatures');
                                if (result.signatures.length === 0) {{
                                    signaturesDiv.innerHTML = '<h3>Подписи отсутствуют</h3>';
                                }} else {{
                                    let html = '<h3>Подписи контракта:</h3>';
                                    result.signatures.forEach(sig => {{
                                        const status = sig.is_valid ? 'Валидна' : 'Невалидна';
                                        const statusClass = sig.is_valid ? 'success' : 'error';
                                        html += `
                                            <div class="contract-info">
                                                <p><strong>ИИН:</strong> ${{sig.signer_iin}}</p>
                                                <p><strong>Дата:</strong> ${{new Date(sig.signed_at).toLocaleString()}}</p>
                                                <p><strong>Статус:</strong> <span class="${{statusClass}}">${{status}}</span></p>
                                                <p><strong>ID:</strong> ${{sig.signature_uid}}</p>
                                            </div>
                                        `;
                                    }});
                                    signaturesDiv.innerHTML = html;
                                }}
                                log('Подписи загружены: ' + result.signatures.length);
                            }} else {{
                                document.getElementById('message').innerHTML = '<div class="error">Ошибка: ' + result.error + '</div>';
                            }}
                        }} catch (error) {{
                            document.getElementById('message').innerHTML = '<div class="error">Ошибка: ' + error.message + '</div>';
                            log('Ошибка: ' + error.message);
                        }}
                    }}

                    function getCookie(name) {{
                        let cookieValue = null;
                        if (document.cookie && document.cookie !== '') {{
                            const cookies = document.cookie.split(';');
                            for (let i = 0; i < cookies.length; i++) {{
                                const cookie = cookies[i].trim();
                                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                    break;
                                }}
                            }}
                        }}
                        return cookieValue;
                    }}

                    // Загружаем подписи при загрузке страницы
                    window.onload = () => {{
                        checkSignatures();
                    }};
                </script>
            </body>
            </html>
            """

            return HttpResponse(html_content, content_type='text/html')

        except ContractMS.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Контракт не найден'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)