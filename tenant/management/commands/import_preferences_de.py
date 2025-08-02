# tenant/management/commands/import_preferences_de.py

import json, os
from django.core.management.base import BaseCommand, CommandError
from parler.utils.context import switch_language

from tenant.models import TenantPreferenceQuestionModel, TenantPreferenceOptionModel

class Command(BaseCommand):
    help = "Import German translations for tenant preference questions & options"

    def add_arguments(self, parser):
        parser.add_argument("--en", required=True, help="Path to English JSON file")
        parser.add_argument("--de", required=True, help="Path to German JSON file")

    def handle(self, *args, **opts):
        path_en = opts["en"]
        path_de = opts["de"]
        for p in (path_en, path_de):
            if not os.path.exists(p):
                raise CommandError(f"File not found: {p}")

        data_en = json.load(open(path_en, encoding="utf-8")).get("data", [])
        data_de = json.load(open(path_de, encoding="utf-8")).get("data", [])

        # Build map: English text → question instance
        q_map = {}
        for q_obj in TenantPreferenceQuestionModel.objects.all():
            # fetch its English translation
            en_text = q_obj.safe_translation_getter("text", language_code="en")
            if en_text:
                q_map[en_text] = q_obj

        # Now loop German JSON
        for de_q in data_de:
            en_text = None
            # find matching English text in the English file by ID
            for q_en in data_en:
                if q_en["id"] == de_q["id"]:
                    en_text = q_en["question_text"]
                    break
            if not en_text:
                self.stdout.write(self.style.WARNING(
                    f"No English JSON entry for German question id={de_q['id']}"
                ))
                continue

            question = q_map.get(en_text)
            if not question:
                self.stdout.write(self.style.WARNING(
                    f"Question instance not found for English text '{en_text}'"
                ))
                continue

            # German translation on question
            with switch_language(question, "de"):
                question.text = de_q["question_text"]
                question.save()
            self.stdout.write(f"Set German text for question id={question.pk}")

            # Build map of option English text → option instance
            opt_map = {}
            for opt in question.options.all():
                en_o = opt.safe_translation_getter("text", language_code="en")
                if en_o:
                    opt_map[en_o] = opt

            # Update each German option
            for de_o in de_q["question_options"]:
                # find matching English text by ID in English JSON
                for o_en in next(q for q in data_en if q["id"] == de_q["id"])["question_options"]:
                    if o_en["id"] == de_o["id"]:
                        en_o_text = o_en["option_text"]
                        break
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  No English JSON entry for option id={de_o['id']} under q id={de_q['id']}"
                    ))
                    continue

                opt = opt_map.get(en_o_text)
                if not opt:
                    self.stdout.write(self.style.WARNING(
                        f"  Option instance not found for English text '{en_o_text}'"
                    ))
                    continue

                with switch_language(opt, "de"):
                    opt.text = de_o["option_text"]
                    opt.save()
                self.stdout.write(f"  Set German text for option id={opt.pk}")

        self.stdout.write(self.style.SUCCESS("German import complete."))
