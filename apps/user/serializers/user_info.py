import io

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import UserInfo, UserDocFile


class UserDocFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocFile
        fields = ['file']
        kwargs = {
            'file': {
                'write_only': True,
                'required': False,
                'allow_null': True,
                'allow_empty_file': True,
            }
        }


class UserInfoSerializer(serializers.ModelSerializer):
    """ uploaded_files not required """

    user_files = serializers.SerializerMethodField()
    photo_avatar = serializers.SerializerMethodField()

    def get_user_files(self, obj):
        files = UserDocFile.objects.filter(user=obj)
        if files:
            return UserDocFileSerializer(files, many=True).data
        return None

    def get_photo_avatar(self, obj):
        if obj.photo_avatar:
            return obj.photo_avatar.url
        return None
    
    uploaded_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=True, use_url=False, allow_null=True),
        write_only=True,
        required=False
    )

    class Meta:
        model = UserInfo
        fields = ['user', 'photo_avatar', 'address', 'contacts', 'email', 'iin', 'num_of_doc', 'issued_by',
                  'issue_date', 'work_place', 'work_position', 'is_teacher', 'is_deleted', 'user_files', 'uploaded_files']

    def create(self, validated_data):
        """ uploaded_files not required """

        if 'uploaded_files' not in validated_data:
            return UserInfo.objects.create(**validated_data)

        uploaded_files = validated_data.pop('uploaded_files', None)
        user = UserInfo.objects.create(**validated_data)

        user_files = [
            UserDocFile(user=user, file=file) for file in uploaded_files
        ]

        for file in user_files:
            file.full_clean()

        try:
            with transaction.atomic():
                UserDocFile.objects.bulk_create(user_files)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return user
