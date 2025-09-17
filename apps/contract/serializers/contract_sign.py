from rest_framework import serializers
from django.contrib.auth.models import User

from apps.contract.models import ContractMS, ContractFileUser, ContractSignature, ContractDopMS, ContractDopFileUser
from apps.contract.serializers.student import StudentMSSerializer


class SignContractWithEDSSerializer(serializers.ModelSerializer):
    """ Сериализация данных договора для подписи ЭЦП """

    certificate = serializers.FileField(required=True, allow_null=False, allow_empty_file=False)
    password = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    class Meta:
        model = ContractMS
        fields = ('certificate', 'password')


class CreateSignContractWithEDSSerializer(serializers.ModelSerializer):
    """ Сериализация данных договора для подписи ЭЦП """

    certificate_data = serializers.FileField(required=True, allow_null=False, allow_empty_file=False)
    password = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    class Meta:
        model = ContractMS
        fields = ('certificate_data', 'password')


class ContractFileUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractFileUser
        fields = '__all__'


class ContractDopFileUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDopFileUser
        fields = '__all__'


class ContractSignatureSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра подписей"""

    signer_type = serializers.SerializerMethodField()
    contract_info = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = ContractSignature
        fields = [
            'signature_uid', 'contract_num', 'signer_iin', 'signer_type',
            'signed_at', 'verified_at', 'is_valid', 'is_document_modified',
            'certificate_info', 'contract_info', 'verification_status'
        ]
        read_only_fields = ('signed_at', 'verified_at', 'signature_uid')

    def get_signer_type(self, obj):
        """Определяет тип подписанта"""
        if obj.created_by is None:
            return 'director'  # Системная подпись директора
        else:
            return 'parent'  # Подпись родителя

    def get_contract_info(self, obj):
        """Получает информацию о контракте"""
        try:
            # Определяем тип контракта
            is_dop_contract = self._is_additional_contract(obj.contract_num)

            if is_dop_contract:
                contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                    agreement_id__ContractNum=obj.contract_num
                ).first()
                if contract_dop:
                    contract = contract_dop.agreement_id
                    return {
                        'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract,
                                                                                                'StudentID') and contract.StudentID else '',
                        'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                        'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                        'contract_status': getattr(contract.ContractStatusID, 'sStatusName', '') if hasattr(contract,
                                                                                                            'ContractStatusID') and contract.ContractStatusID else '',
                        'contract_type': 'Дополнительный договор',
                        'dop_amount': str(contract_dop.amount) if contract_dop.amount else '',
                        'description': contract_dop.description or ''
                    }
            else:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=obj.contract_num)
                return {
                    'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract,
                                                                                            'StudentID') and contract.StudentID else '',
                    'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                    'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                    'contract_status': getattr(contract.ContractStatusID, 'sStatusName', '') if hasattr(contract,
                                                                                                        'ContractStatusID') and contract.ContractStatusID else '',
                    'contract_type': 'Основной договор'
                }
        except:
            return {
                'student_name': 'Информация недоступна',
                'contract_amount': '',
                'contract_date': '',
                'contract_status': '',
                'contract_type': 'Неизвестно'
            }

    def get_verification_status(self, obj):
        """Определяет статус верификации подписи"""
        if not obj.is_valid:
            if obj.is_document_modified:
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

    def _is_additional_contract(self, contract_num: str) -> bool:
        """Определяет является ли договор дополнительным по номеру"""
        return 'Д' in contract_num or '/' in contract_num


class ContractSignatureCreateSerializer(serializers.Serializer):
    """Сериализатор для создания подписи через новый API"""

    contract_num = serializers.CharField(max_length=255)
    cms = serializers.CharField()
    data = serializers.CharField()
    is_dop_contract = serializers.BooleanField(default=False)

    def validate_contract_num(self, value):
        """Проверяем существование контракта"""
        is_dop_contract = 'Д' in value or '/' in value

        try:
            if is_dop_contract:
                contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                    agreement_id__ContractNum=value
                ).first()
                if not contract_dop:
                    raise serializers.ValidationError("Дополнительный договор не найден")
            else:
                ContractMS.objects.using('ms_sql').get(ContractNum=value)
        except ContractMS.DoesNotExist:
            raise serializers.ValidationError("Контракт не найден")

        return value

    def validate(self, data):
        """Дополнительная валидация"""
        contract_num = data['contract_num']
        is_dop_contract = data.get('is_dop_contract', False)

        # Автоматически определяем тип контракта если не указано
        if not is_dop_contract and ('Д' in contract_num or '/' in contract_num):
            data['is_dop_contract'] = True

        return data


class SignatureVerificationResponseSerializer(serializers.Serializer):
    """Сериализатор ответа для проверки подписи"""

    success = serializers.BooleanField()
    signature_info = ContractSignatureSerializer(required=False)
    error = serializers.CharField(required=False)
    error_code = serializers.CharField(required=False)


class ContractSignaturesResponseSerializer(serializers.Serializer):
    """Сериализатор ответа со списком подписей контракта"""

    success = serializers.BooleanField()
    contract_num = serializers.CharField()
    signature_status = serializers.CharField()
    signatures = ContractSignatureSerializer(many=True)
    total_signatures = serializers.IntegerField()
    valid_signatures = serializers.IntegerField()
    error = serializers.CharField(required=False)
    error_code = serializers.CharField(required=False)


class ContractSigningDataSerializer(serializers.Serializer):
    """Сериализатор для данных подписания контракта"""

    contract_num = serializers.CharField()
    data = serializers.CharField()  # Base64 encoded data
    hash = serializers.CharField()  # SHA256 hash
    is_dop_contract = serializers.BooleanField()
    contract_info = serializers.DictField()


class ContractSigningResponseSerializer(serializers.Serializer):
    """Сериализатор ответа подписания контракта"""

    success = serializers.BooleanField()
    signature_uid = serializers.CharField(required=False)
    signer_iin = serializers.CharField(required=False)
    contract_num = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    error_code = serializers.CharField(required=False)


class QRCodeDataSerializer(serializers.Serializer):
    """Сериализатор для данных QR-кода"""

    type = serializers.CharField()
    signature_uid = serializers.CharField(required=False)
    contract_num = serializers.CharField()
    signer_iin = serializers.CharField(required=False)
    signed_at = serializers.CharField()
    verification_url = serializers.CharField(required=False)
    message = serializers.CharField(required=False)

    # Для QR-кодов директоров
    director = serializers.CharField(required=False)
    position = serializers.CharField(required=False)
    certificate_info = serializers.DictField(required=False)


class DirectorSignatureDataSerializer(serializers.Serializer):
    """Сериализатор для данных подписи директора"""

    iin = serializers.CharField(max_length=12)
    full_name = serializers.CharField()
    position = serializers.CharField()
    certificate_info = serializers.DictField()
    cms_signature = serializers.CharField(required=False)
    signed_data = serializers.CharField(required=False)