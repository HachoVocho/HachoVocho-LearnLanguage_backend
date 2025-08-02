import json, os
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from parler.utils.context import switch_language

from user.models import (
    OccupationModel,
    ReligionModel,
    IncomeRangeModel,
    SmokingHabitModel,
    DrinkingHabitModel,
    SocializingHabitModel,
    RelationshipStatusModel,
    FoodHabitModel,
)

LOOKUP_SETS = {
    "occupations": OccupationModel,
    "religions": ReligionModel,
    "income_ranges": IncomeRangeModel,
    "smoking_habits": SmokingHabitModel,
    "drinking_habits": DrinkingHabitModel,
    "socializing_habits": SocializingHabitModel,
    "relationship_statuses": RelationshipStatusModel,
    "food_habits": FoodHabitModel,
}

class Command(BaseCommand):
    help = "Import personality lookup tables (Occupation, Religion, etc.) in EN + DE"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", "-f", required=True,
            help="Path to JSON file defining all sets",
        )

    def handle(self, *args, **opts):
        path = opts["file"]
        if not os.path.exists(path):
            raise CommandError(f"File not found: {path}")

        payload = json.load(open(path, encoding="utf-8"))

        for section, Model in LOOKUP_SETS.items():
            entries = payload.get(section, [])
            if not entries:
                continue
            self.stdout.write(f"\n→ {section.replace('_',' ').title()}:")
            for entry in entries:
                en_title = entry["en"].strip()
                # 1) find existing by english translation
                obj = (
                    Model.objects
                    .language("en")
                    .filter(translations__title=en_title)
                    .first()
                )
                if obj:
                    created = False
                    self.stdout.write(f"  • Updating “{en_title}”")
                else:
                    # 2) create a new one
                    obj = Model.objects.create(
                        is_active=True,
                        created_at=now()
                    )
                    created = True
                    self.stdout.write(f"  • Created “{en_title}”")

                # 3) write both EN and DE
                for lang in ("en", "de"):
                    with switch_language(obj, lang):
                        obj.title = entry[lang]
                        obj.save()

                # 4) special: income ranges may carry numbers
                if section == "income_ranges":
                    obj.min_income = entry.get("min_income")
                    obj.max_income = entry.get("max_income")
                    obj.save()

        self.stdout.write(self.style.SUCCESS("\n🎉 All lookups imported!"))
