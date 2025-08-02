# appointments/management/commands/populate_status_translations.py

from django.core.management.base import BaseCommand
from django.utils import translation
from appointments.models import AppointmentBookingModel

class Command(BaseCommand):
    help = "Populate German (de) translations for AppointmentBookingModel.status_label"

    GERMAN = {
        "pending":   "Ausstehend",
        "confirmed": "Bestätigt",
        "cancelled": "Abgesagt",
        "completed": "Abgeschlossen",
        "declined":  "Abgelehnt",
    }

    def handle(self, *args, **options):
        total = AppointmentBookingModel.objects.count()
        self.stdout.write(f"Found {total} appointments. Writing German translations…")
        for i, booking in enumerate(AppointmentBookingModel.objects.all(), 1):
            code = booking.status
            de_label = self.GERMAN.get(code)
            if not de_label:
                self.stdout.write(self.style.WARNING(
                    f"  • Skipping #{booking.id}: unknown status “{code}”"
                ))
                continue

            booking.set_current_language('de')
            booking.status_label = de_label
            booking.save()  # Parler will create or update the translation row
            self.stdout.write(f"  ✓ #{booking.id}: {code} → {de_label} ({i}/{total})")

        translation.deactivate()
        self.stdout.write(self.style.SUCCESS("Done. All German labels populated."))
