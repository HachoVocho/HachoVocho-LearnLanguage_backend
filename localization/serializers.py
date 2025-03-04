from rest_framework import serializers
from .models import CityModel

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CityModel
        fields = ['id', 'name', 'state', 'latitude', 'longitude']
