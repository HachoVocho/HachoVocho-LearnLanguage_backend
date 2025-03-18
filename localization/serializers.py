from rest_framework import serializers
from .models import CityModel, CountryModel

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CityModel
        fields = ['id', 'name', 'state', 'latitude', 'longitude']


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryModel
        fields = ['id', 'name']
