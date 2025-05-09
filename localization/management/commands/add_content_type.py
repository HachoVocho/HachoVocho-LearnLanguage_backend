# your_app/management/commands/fix_country_contenttype.py

from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from localization.models import CountryModel
from landlord.models import LandlordQuestionModel

class Command(BaseCommand):
    help = (
        "Fixes any stale ContentType for CountryModel and re-assigns it "
        "to all LandlordQuestionModel objects that should point at it."
    )

    def handle(self, *args, **options):
        # 1) Get the correct ContentType for CountryModel
        correct_ct, created = ContentType.objects.get_or_create(
            app_label=CountryModel._meta.app_label,
            model=CountryModel._meta.model_name
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created new ContentType for {CountryModel._meta.label}."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Found existing ContentType (id={correct_ct.pk}) for {CountryModel._meta.label}."
            ))

        # 2) Optionally remove any stale ContentType rows for CountryModel
        stale = ContentType.objects.filter(
            app_label=CountryModel._meta.app_label,
        ).exclude(pk=correct_ct.pk).filter(model__iexact='countriesmodel')
        count = stale.count()
        if count:
            stale.delete()
            self.stdout.write(self.style.WARNING(
                f"Removed {count} stale ContentType row(s) with model='countriesmodel'."
            ))

        # 3) Find any questions that logically belong to CountryModel but have wrong/missing ct
        qs = LandlordQuestionModel.objects.filter(
            question_text__icontains='country',  # adjust your own filter
        ).exclude(content_type=correct_ct)

        updated = 0
        for q in qs:
            old = q.content_type
            q.content_type = correct_ct
            q.save(update_fields=['content_type'])
            updated += 1
            self.stdout.write(
                f"Re-pointed question id={q.pk!r} "
                f"('{q.question_text[:30]}…') from ct={old!r} to ct={correct_ct.pk}."
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done. Re-assigned {updated} question(s) to ContentType id={correct_ct.pk}."
        ))
