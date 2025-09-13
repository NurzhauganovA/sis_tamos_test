from rest_framework import serializers

from apps.contract.models import ContractMS, ContractFileUser, ContractSignature
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


class ContractSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractSignature
        fields = '__all__'
        read_only_fields = ('signed_at',)


class ContractSignatureCreateSerializer(serializers.Serializer):
    """Сериализатор для создания подписи через FastAPI"""
    contract_file_id = serializers.IntegerField()
    contract_id = serializers.IntegerField(required=False, allow_null=True)
    signer_iin = serializers.CharField(max_length=12)
    cms_signature = serializers.CharField()
    original_file_hash = serializers.CharField(max_length=64)
    signature_uid = serializers.CharField(max_length=255)