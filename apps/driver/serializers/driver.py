from rest_framework import serializers

from ..models import Route, Transport, Driver, HistoryDriver
from ...student.models import Student
from ...user.models import User, UserInfo


class TransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transport
        fields = ['transport_model', 'transport_number', 'number_of_seats']


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['full_name', 'phone']


class SeniorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['fio', 'login']


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = ['address', 'contacts']


class UserSerializer(serializers.ModelSerializer):
    parent_info = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['parent_info']

    def get_parent_info(self, obj):
        parent_info = obj.parent_info_user.first()  # Get the first related ParentInfo instance
        if parent_info:
            return ParentSerializer(parent_info).data
        return None


class ChildrenSerializer(serializers.ModelSerializer):
    parent = UserSerializer(read_only=True)

    class Meta:
        model = Student
        fields = ['full_name', 'phone', 'stud_class', 'parent']


class RouteSerializer(serializers.ModelSerializer):
    transport = TransportSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    senior = SeniorSerializer(read_only=True)
    children = ChildrenSerializer(read_only=True, many=True)

    class Meta:
        model = Route
        fields = ['id', 'name', 'transport', 'driver', 'senior', 'children', 'is_active']


class HistoryDriverSerializer(serializers.ModelSerializer):
    transport = TransportSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    date = serializers.DateTimeField(format="%d.%m.%Y %H:%M:%S")

    class Meta:
        model = HistoryDriver
        fields = ['transport', 'driver', 'date']
