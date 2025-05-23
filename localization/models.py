from django.db import models
from django.utils.timezone import now

class CountryModel(models.Model):
    name = models.CharField(max_length=100)
    iso3 = models.CharField(max_length=3, blank=True, null=True)
    iso2 = models.CharField(max_length=2, blank=True, null=True)
    numeric_code = models.CharField(max_length=10, blank=True, null=True)
    phonecode = models.CharField(max_length=20, blank=True, null=True)
    capital = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    currency_name = models.CharField(max_length=100, blank=True, null=True)
    currency_symbol = models.CharField(max_length=10, blank=True, null=True)
    tld = models.CharField(max_length=10, blank=True, null=True)
    native = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    region_id = models.IntegerField(blank=True, null=True)
    subregion = models.CharField(max_length=100, blank=True, null=True)
    subregion_id = models.IntegerField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    emoji = models.CharField(max_length=10, blank=True, null=True)
    emojiU = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=12,     # total digits (incl. decimals)
        decimal_places=2,  # digits after the decimal point
        blank=True,
        null=True,
    )
    def __str__(self):
        return self.name


class CountryTranslationModel(models.Model):
    country = models.ForeignKey(CountryModel, on_delete=models.CASCADE, related_name='translations')
    language_code = models.CharField(max_length=10)
    translation = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.country.name} - {self.language_code}"


class TimezoneModel(models.Model):
    country = models.ForeignKey(CountryModel, on_delete=models.CASCADE, related_name='timezones')
    zone_name = models.CharField(max_length=100)
    gmt_offset = models.IntegerField()
    gmt_offset_name = models.CharField(max_length=20)
    abbreviation = models.CharField(max_length=10)
    tz_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.zone_name} ({self.country.name})"


class StateModel(models.Model):
    country = models.ForeignKey(CountryModel, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=10, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    state_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.country.name}"


class CityModel(models.Model):
    state = models.ForeignKey(StateModel, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name}, {self.state.name}"
