from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import AdditionalParent, AdditionalParentUserDocFile


class AdditionalParentUserDocFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalParentUserDocFile
        fields = ['file']
        kwargs = {
            'file': {
                'write_only': True,
                'required': False,
                'allow_null': True,
                'allow_empty_file': True,
            }
        }


class AdditionalParentSerializer(serializers.ModelSerializer):
    """ uploaded_files not required """

    additional_parent_user_files = AdditionalParentUserDocFileSerializer(many=True, read_only=True)

    uploaded_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=True, use_url=False, allow_null=True),
        write_only=True,
        required=False
    )

    class Meta:
        model = AdditionalParent
        fields = ['id', 'main_user', 'photo_avatar', 'phone_number', 'email', 'full_name', 'address', 'iin', 'num_of_doc', 'is_teacher',
                  'issued_by', 'issue_date', 'contacts', 'additional_parent_user_files', 'uploaded_files']

    def create(self, validated_data):
        """ uploaded_files not required """

        if 'uploaded_files' not in validated_data:
            return AdditionalParent.objects.create(**validated_data)

        uploaded_files = validated_data.pop('uploaded_files', None)
        additional_parent_user = AdditionalParent.objects.create(**validated_data)

        additional_parent_user_files = [
            AdditionalParentUserDocFile(additional_parent_user=additional_parent_user, file=file) for file in uploaded_files
        ]

        for file in additional_parent_user_files:
            file.full_clean()

        try:
            with transaction.atomic():
                AdditionalParentUserDocFile.objects.bulk_create(additional_parent_user_files)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return additional_parent_user
