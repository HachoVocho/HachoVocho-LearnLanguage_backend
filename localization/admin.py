from django.contrib import admin
from .models import (
    CountryModel,
    CountryTranslationModel,
    TimezoneModel,
    StateModel,
    CityModel
)


@admin.register(CountryModel)
class CountryModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'iso2', 'iso3', 'phonecode', 'capital',
        'region', 'subregion'
    )
    search_fields = (
        'name', 'iso2', 'iso3', 'phonecode', 'capital',
        'region', 'subregion'
    )
    ordering = ('id',)


@admin.register(CountryTranslationModel)
class CountryTranslationModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'country', 'language_code', 'translation'
    )
    search_fields = (
        'country__name', 'language_code', 'translation'
    )
    ordering = ('id',)


@admin.register(TimezoneModel)
class TimezoneModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'country', 'zone_name', 'gmt_offset',
        'gmt_offset_name', 'abbreviation', 'tz_name'
    )
    search_fields = (
        'country__name', 'zone_name', 'gmt_offset_name',
        'abbreviation', 'tz_name'
    )
    ordering = ('id',)


@admin.register(StateModel)
class StateModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'state_code', 'country', 'state_type'
    )
    search_fields = (
        'name', 'state_code', 'country__name', 'state_type'
    )
    ordering = ('id',)


@admin.register(CityModel)
class CityModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'state', 'latitude', 'longitude'
    )
    search_fields = (
        'name', 'state__name'
    )
    ordering = ('id',)
