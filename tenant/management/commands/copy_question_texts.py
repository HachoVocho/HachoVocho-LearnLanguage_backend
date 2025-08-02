from django.core.management.base import BaseCommand
from tenant.models import (
    TenantPreferenceQuestionModel,
    TenantPreferenceQuestionTextModel,
    LanguageModel
)

class Command(BaseCommand):
    help = "Backfill question_text_new from the old fields"

    def handle(self, *args, **options):
        # You already have language codes per row, so just re‑use them
        for q in TenantPreferenceQuestionModel.objects.all():
            txt = TenantPreferenceQuestionTextModel.objects.create(
                text     = q.question_text,
                language = q.language
            )
            q.question_text_new = txt
            q.save(update_fields=["question_text_new"])
        self.stdout.write(self.style.SUCCESS("Done back‑filling text!"))
