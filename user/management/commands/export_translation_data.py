# management/commands/export_translation_data.py
from django.utils import timezone
import json
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from translations.models import LanguageModel
from user.models import (
    OccupationModel, ReligionModel, IncomeRangeModel,
    SmokingHabitModel, DrinkingHabitModel,
    SocializingHabitModel, RelationshipStatusModel,
    FoodHabitModel
)
from django.utils.timezone import now
class Command(BaseCommand):
    help = 'Export all translation data to JSON'

    def handle(self, *args, **options):
        with open('/Users/anirudhchawla/django_projects/HachoVocho-Housing_backend/translation_data_english.json') as f:
            data = json.load(f)
        
        # Get or create German language
        german_lang, _ = LanguageModel.objects.get_or_create(
            code='de',
            defaults={'name': 'German'}
        )
        
        # Model mapping
        model_mapping = {
            'OccupationModel': OccupationModel,
            'ReligionModel': ReligionModel,
            'IncomeRangeModel': IncomeRangeModel,
            'SmokingHabitModel': SmokingHabitModel,
            'DrinkingHabitModel': DrinkingHabitModel,
            'SocializingHabitModel': SocializingHabitModel,
            'RelationshipStatusModel': RelationshipStatusModel,
            'FoodHabitModel': FoodHabitModel
        }
        
        for model_name, items in data.items():
            model = model_mapping[model_name]
            print(f"\nProcessing {model.__name__}...")
            
            for item in items:
                # Try to find existing English entry
                # inside your loop, for each `item` and `model`:

                german_entry = model.objects.filter(id=item['id'], language__code='de').first()

                if german_entry:
                    # update the existing German translation
                    german_entry.title = item['title_de']
                    german_entry.save(update_fields=['title'])
                    print(f"Updated {model.__name__}#{item['id']} to “{item['title_de']}”")
                else:
                    # create a new German row
                    model.objects.create(
                        title=item['title_de'],
                        language_id='de',        # FK to Language.code
                        is_active=True,
                        is_deleted=False,
                        created_at=timezone.now(),
                    )
                    print(f"Created {model.__name__}#{item['id']} as “{item['title_de']}”")


        print("\nGerman translations updated successfully!")

        
        self.stdout.write(self.style.SUCCESS('Successfully exported translation data to translation_data_english.json'))