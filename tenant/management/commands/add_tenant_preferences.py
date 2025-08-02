import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from tenant.models import (
    LanguageModel,
    TenantPreferenceQuestionTextModel,
    TenantPreferenceQuestionTypeModel,
    TenantPreferenceQuestionModel,
    TenantPreferenceQuestionOptionTextModel,
    TenantPreferenceOptionModel,
)


class Command(BaseCommand):
    help = 'Import tenant preference questions and options from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the JSON file containing preference questions.'
        )
        parser.add_argument(
            '--language',
            type=str,
            default='en',
            help='Language code for text entries (default: en).'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        lang_code = options['language']

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise CommandError(f'Error reading JSON file: {e}')

        # Ensure language exists
        language, _ = LanguageModel.objects.get_or_create(code=lang_code)

        for item in data.get('data', []):
            q_text = item.get('question_text')
            q_type_data = item.get('question_type')

            # Create or get question text
            question_text_obj, created = TenantPreferenceQuestionTextModel.objects.get_or_create(
                text=q_text,
                language=language,
                defaults={'created_at': now(), 'is_active': True, 'is_deleted': False}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created QuestionText: {q_text}'))

            # Fetch question type model
            try:
                q_type = TenantPreferenceQuestionTypeModel.objects.get(id=q_type_data['id'])
            except TenantPreferenceQuestionTypeModel.DoesNotExist:
                raise CommandError(f"QuestionType with id {q_type_data['id']} not found.")

            # Create or get question
            question_obj, created_q = TenantPreferenceQuestionModel.objects.get_or_create(
                question_text=question_text_obj,
                question_type=q_type,
                defaults={'created_at': now(), 'is_active': True, 'is_deleted': False}
            )
            if created_q:
                self.stdout.write(self.style.SUCCESS(f'Created Question: {q_text}'))

            # Process options
            for opt in item.get('question_options', []):
                opt_text = opt.get('option_text')

                # Create or get option text
                option_text_obj, created_opt_text = TenantPreferenceQuestionOptionTextModel.objects.get_or_create(
                    text=opt_text,
                    language=language,
                    defaults={'created_at': now(), 'is_active': True, 'is_deleted': False}
                )
                if created_opt_text:
                    self.stdout.write(self.style.SUCCESS(f'Created OptionText: {opt_text}'))

                # Create or get option model
                option_obj, created_opt = TenantPreferenceOptionModel.objects.get_or_create(
                    question=question_obj,
                    option_text=option_text_obj,
                    defaults={'created_at': now(), 'is_active': True, 'is_deleted': False}
                )
                if created_opt:
                    self.stdout.write(self.style.SUCCESS(f'  Added Option: {opt_text} to Question: {q_text}'))

        self.stdout.write(self.style.SUCCESS('Import completed successfully.'))
