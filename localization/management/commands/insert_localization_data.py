import json
from django.core.management.base import BaseCommand
from localization.models import (
    CountryModel,
    CountryTranslationModel,
    TimezoneModel,
    StateModel,
    CityModel
)


class Command(BaseCommand):
    help = "Load multiple countries (and their states/cities/timezones/translations) from a JSON file."

    def handle(self, *args, **options):
        """
        Expects 'testing.json' to contain an array/list of countries, e.g.:
        [
            {
                "id": 1,
                "name": "Afghanistan",
                "iso3": "AFG",
                "iso2": "AF",
                ...
                "states": [...],
                "timezones": [...],
                "translations": {...}
            },
            {
                "id": 2,
                "name": "Albania",
                "iso3": "ALB",
                "iso2": "AL",
                ...
                "states": [...],
                "timezones": [...],
                "translations": {...}
            }
            ...
        ]
        """

        with open('testing.json', 'r', encoding='utf-8') as f:
            all_countries_data = json.load(f)

        for country_data in all_countries_data:
            # 1. Create or get the Country record
            country, created = CountryModel.objects.get_or_create(
                name=country_data.get("name"),
                defaults={
                    'iso3': country_data.get("iso3"),
                    'iso2': country_data.get("iso2"),
                    'numeric_code': country_data.get("numeric_code"),
                    'phonecode': country_data.get("phonecode"),
                    'capital': country_data.get("capital"),
                    'currency': country_data.get("currency"),
                    'currency_name': country_data.get("currency_name"),
                    'currency_symbol': country_data.get("currency_symbol"),
                    'tld': country_data.get("tld"),
                    'native': country_data.get("native"),
                    'region': country_data.get("region"),
                    'region_id': country_data.get("region_id"),
                    'subregion': country_data.get("subregion"),
                    'subregion_id': country_data.get("subregion_id"),
                    'nationality': country_data.get("nationality"),
                    'latitude': country_data.get("latitude"),
                    'longitude': country_data.get("longitude"),
                    'emoji': country_data.get("emoji"),
                    'emojiU': country_data.get("emojiU"),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Country: {country.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Country already exists: {country.name}"))

            # 2. Create Translations
            translations = country_data.get("translations", {})
            for lang_code, translation_value in translations.items():
                CountryTranslationModel.objects.create(
                    country=country,
                    language_code=lang_code,
                    translation=translation_value
                )

            # 3. Create Timezones
            timezones = country_data.get("timezones", [])
            for tz_data in timezones:
                TimezoneModel.objects.create(
                    country=country,
                    zone_name=tz_data.get("zoneName"),
                    gmt_offset=tz_data.get("gmtOffset"),
                    gmt_offset_name=tz_data.get("gmtOffsetName"),
                    abbreviation=tz_data.get("abbreviation"),
                    tz_name=tz_data.get("tzName")
                )

            # 4. Create States and their Cities
            states = country_data.get("states", [])
            for state_data in states:
                state_obj = StateModel.objects.create(
                    country=country,
                    name=state_data.get("name"),
                    state_code=state_data.get("state_code"),
                    latitude=state_data.get("latitude"),
                    longitude=state_data.get("longitude"),
                    state_type=state_data.get("type")
                )
                
                cities = state_data.get("cities", [])
                for city_data in cities:
                    CityModel.objects.create(
                        state=state_obj,
                        name=city_data.get("name"),
                        latitude=city_data.get("latitude"),
                        longitude=city_data.get("longitude")
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed country: {country.name} (States: {len(states)})"
                )
            )

        self.stdout.write(self.style.SUCCESS("All country data loaded successfully!"))
