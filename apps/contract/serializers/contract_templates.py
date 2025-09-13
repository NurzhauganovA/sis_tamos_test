from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from apps.contract.models import MarkedUpContractTemplate, RawContractTemplate
from apps.contract import ContractVariable


class RawContractTemplateSerializer(ModelSerializer):

    class Meta:
        model = RawContractTemplate
        fields = (
            'id',
            'file',
            'school',
            'name',
            'created_at',
            'changed_at',
        )
        read_only_fields = (
            'created_at',
            'changed_at',
        )


class RawContractTemplateForMarkUpSerializer(ModelSerializer):
    variables_list = serializers.SerializerMethodField()

    class Meta:
        model = RawContractTemplate
        fields = (
            'id',
            'file',
            'name',
            'created_at',
            'changed_at',
            'variables_list',
        )
        read_only_fields = (
            'created_at',
            'changed_at',
            'variables_list',
        )

    def get_variables_list(self, obj: RawContractTemplate) -> list:
        return ContractVariable.choices


class MarkedUpContractTemplateSerializer(ModelSerializer):

    class Meta:
        model = MarkedUpContractTemplate
        fields = (
            'id',
            'file',
            'name',
            'school',
            'created_at',
            'changed_at',
        )
        read_only_fields = (
            'created_at',
            'changed_at',
        )
