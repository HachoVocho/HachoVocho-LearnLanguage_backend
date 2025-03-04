from django.core.management.base import BaseCommand
from django.utils.timezone import now
from user.models import (
    OccupationModel,
    ReligionModel,
    IncomeRangeModel,
    SmokingHabitModel,
    DrinkingHabitModel,
    SocializingHabitModel,
    RelationshipStatusModel,
    FoodHabitModel
)

class Command(BaseCommand):
    help = 'Adds options to specified models if they do not already exist'

    def handle(self, *args, **kwargs):
        # Add options for the OccupationModel
        occupations = ["Student", "Working professional", "Retired", "Unemployed"]
        for occupation in occupations:
            if not OccupationModel.objects.filter(title=occupation).exists():
                OccupationModel.objects.create(
                    title=occupation,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Occupation: {occupation}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Occupation '{occupation}' already exists"))

        # Add options for the ReligionModel
        religions = ["Christianity", "Islam", "Hinduism", "Buddhism", "Other"]
        for religion in religions:
            if not ReligionModel.objects.filter(title=religion).exists():
                ReligionModel.objects.create(
                    title=religion,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Religion: {religion}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Religion '{religion}' already exists"))

        # Add options for the IncomeRangeModel (without currency symbol)
        income_ranges = [
            {"title": "Below 30000", "min_income": 0, "max_income": 30000},
            {"title": "30000-60000", "min_income": 30000, "max_income": 60000},
            {"title": "60000-100000", "min_income": 60000, "max_income": 100000},
            {"title": "Above 100000", "min_income": 100000, "max_income": None}
        ]
        for income_range in income_ranges:
            if not IncomeRangeModel.objects.filter(title=income_range["title"]).exists():
                IncomeRangeModel.objects.create(
                    title=income_range["title"],
                    min_income=income_range["min_income"],
                    max_income=income_range["max_income"],
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Income Range: {income_range['title']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Income Range '{income_range['title']}' already exists"))

        # Add options for the SmokingHabitModel
        smoking_habits = ["Non-smoker", "Occasional smoker", "Regular smoker"]
        for smoking_habit in smoking_habits:
            if not SmokingHabitModel.objects.filter(title=smoking_habit).exists():
                SmokingHabitModel.objects.create(
                    title=smoking_habit,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Smoking Habit: {smoking_habit}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Smoking Habit '{smoking_habit}' already exists"))

        # Add options for the DrinkingHabitModel
        drinking_habits = ["Non-drinker", "Occasional drinker", "Regular drinker"]
        for drinking_habit in drinking_habits:
            if not DrinkingHabitModel.objects.filter(title=drinking_habit).exists():
                DrinkingHabitModel.objects.create(
                    title=drinking_habit,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Drinking Habit: {drinking_habit}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Drinking Habit '{drinking_habit}' already exists"))

        # Add options for the SocializingHabitModel
        socializing_habits = ["Extroverted", "Introverted", "Moderate"]
        for socializing_habit in socializing_habits:
            if not SocializingHabitModel.objects.filter(title=socializing_habit).exists():
                SocializingHabitModel.objects.create(
                    title=socializing_habit,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Socializing Habit: {socializing_habit}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Socializing Habit '{socializing_habit}' already exists"))

        # Add options for the RelationshipStatusModel
        relationship_statuses = ["Single", "Married", "Divorced", "Widowed"]
        for relationship_status in relationship_statuses:
            if not RelationshipStatusModel.objects.filter(title=relationship_status).exists():
                RelationshipStatusModel.objects.create(
                    title=relationship_status,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Relationship Status: {relationship_status}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Relationship Status '{relationship_status}' already exists"))

        # Add options for the FoodHabitModel
        food_habits = ["Vegetarian", "Vegan", "Non-vegetarian", "Other"]
        for food_habit in food_habits:
            if not FoodHabitModel.objects.filter(title=food_habit).exists():
                FoodHabitModel.objects.create(
                    title=food_habit,
                    is_active=True,
                    is_deleted=False,
                    created_at=now()
                )
                self.stdout.write(self.style.SUCCESS(f"Added Food Habit: {food_habit}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Food Habit '{food_habit}' already exists"))

        self.stdout.write(self.style.SUCCESS("Options have been successfully added or already exist."))
