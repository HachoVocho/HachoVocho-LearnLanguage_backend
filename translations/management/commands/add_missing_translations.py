import os
import re
import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps

class Command(BaseCommand):
    help = 'Extract all static string keys from GlobalStaticStrings dart file and export to CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dart-file',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'global_static_strings.dart'),
            help='Path to your GlobalStaticStrings dart file'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'translations_export.csv'),
            help='Output CSV file path'
        )

    def handle(self, *args, **options):
        dart_path = options['dart_file']
        output_path = options['output']
        # match lines like staticStrings['KEY'] ?? "Default text"
        pattern = re.compile(r"staticStrings\['(?P<key>[^']+)'\]\s*\?\?\s*\"(?P<def>[^\"]*)\"")
        keys = []
        with open(dart_path, 'r', encoding='utf-8') as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    keys.append((m.group('key'), m.group('def')))

        # load existing translation keys
        LanguageModel = apps.get_model('translations', 'LanguageModel')
        TranslationModel = apps.get_model('translations', 'TranslationModel')
        existing_keys = set(TranslationModel.objects.values_list('key', flat=True))

        missing = [(k, d) for k, d in keys if k not in existing_keys]

        with open(output_path, 'w', newline='', encoding='utf-8') as csvf:
            writer = csv.writer(csvf)
            writer.writerow(['key', 'en_value', 'de_value'])
            for key, en in missing:
                writer.writerow([key, en, ''])

        self.stdout.write(self.style.SUCCESS(
            f'Exported {len(missing)} missing keys to {output_path}'
        ))
