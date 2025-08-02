# management/commands/create_translation_template.py
import csv
import json
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Create translation template CSV'

    def handle(self, *args, **options):
        with open('translation_data_english.json') as f:
            data = json.load(f)
        
        with open('translation_template.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['model_name', 'id', 'english_text', 'german_text'])
            
            for model_name, items in data.items():
                for item in items:
                    writer.writerow([
                        model_name,
                        item['id'],
                        item['title'],
                        ''  # Empty for German translations
                    ])
        
        self.stdout.write(self.style.SUCCESS('Created translation_template.csv'))