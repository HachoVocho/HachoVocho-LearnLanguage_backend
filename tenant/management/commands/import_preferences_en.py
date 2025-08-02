# tenant/management/commands/import_preferences_en.py
import json, os
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from parler.utils.context import switch_language

from tenant.models import (
    TenantPreferenceQuestionTypeModel,
    TenantPreferenceQuestionModel,
    TenantPreferenceOptionModel,
)

class Command(BaseCommand):
    help = "Import tenant preference questions & options (English only)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the English JSON file",
        )

    def handle(self, *args, **opts):
        path = opts["file"]
        if not os.path.exists(path):
            raise CommandError(f"File not found: {path}")

        data = json.load(open(path, encoding="utf-8")).get("data", [])

        for q in data:
            qt_name = q["question_type"]["type_name"]
            qtype, _ = TenantPreferenceQuestionTypeModel.objects.get_or_create(
                type_name=qt_name, defaults={"description": ""}
            )

            # Lookup or create by English text
            existing = TenantPreferenceQuestionModel.objects.filter(
                translations__language_code="en",
                translations__text=q["question_text"]
            ).first()

            if existing:
                question = existing
                self.stdout.write(f"Reusing question #{question.pk}")
            else:
                question = TenantPreferenceQuestionModel.objects.create(
                    question_type=qtype,
                    created_at=now(), is_active=True
                )
                self.stdout.write(f"Created question #{question.pk}")
            
            # Set the English translation
            with switch_language(question, "en"):
                question.text = q["question_text"]
                question.save()

            # Now options—always create new ones under this question
            for o in q.get("question_options", []):
                opt = TenantPreferenceOptionModel.objects.create(
                    question=question,
                    created_at=now(), is_active=True
                )
                self.stdout.write(f"  Created option #{opt.pk}")
                with switch_language(opt, "en"):
                    opt.text = o["option_text"]
                    opt.save()

        self.stdout.write(self.style.SUCCESS("English import complete."))
