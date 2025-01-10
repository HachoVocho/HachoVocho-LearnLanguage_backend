from rest_framework import serializers
from .models import UserRoleModel

class UserRoleSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=50)
