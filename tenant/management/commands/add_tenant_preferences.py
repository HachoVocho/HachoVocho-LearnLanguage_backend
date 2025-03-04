# your_app/management/commands/add_tenant_preferences.py

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from tenant.models import (
    TenantPreferenceQuestionTypeModel,
    TenantPreferenceQuestionModel,
    TenantPreferenceOptionModel
)

class Command(BaseCommand):
    help = 'Adds tenant preference questions and options to the database'

    def handle(self, *args, **kwargs):
        # Step 1: Define Question Types
        question_types = [
            {'code': 'single_mcq', 'name': 'Single Choice MCQ'},
            {'code': 'multiple_mcq', 'name': 'Multiple Select MCQ'},
            {'code': 'priority_based', 'name': 'Priority Based'},
        ]

        # Create or get existing question types
        for qt in question_types:
            obj, created = TenantPreferenceQuestionTypeModel.objects.get_or_create(
                type_name=qt['code'],
                defaults={'description': qt['name']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Question Type: {obj.type_name}"))
            else:
                self.stdout.write(f"Question Type already exists: {obj.type_name}")

        # Helper function to get question type instance
        def get_question_type(code):
            try:
                return TenantPreferenceQuestionTypeModel.objects.get(type_name=code)
            except TenantPreferenceQuestionTypeModel.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Question Type '{code}' does not exist. Skipping related questions."))
                return None

        # Step 2: Define Tenant Preference Questions
        tenant_questions = [
            {
                'question_text': "Preferred Property Type",
                'question_type': 'priority_based',
                'options': [
                    "Apartment",
                    "House",
                    "Condo",
                    "Studio",
                    "Shared Accommodation",
                    "Other"
                ]
            },
            {
                'question_text': "Number of Bedrooms",
                'question_type': 'priority_based',
                'options': [
                    "Studio (0 bedrooms)",
                    "1 Bedroom",
                    "2 Bedrooms",
                    "3 Bedrooms",
                    "4+ Bedrooms"
                ]
            },
            {
                'question_text': "Number of Bathrooms",
                'question_type': 'priority_based',
                'options': [
                    "1 Bathroom",
                    "2 Bathrooms",
                    "3+ Bathrooms"
                ]
            },
            {
                'question_text': "Preferred Property Size",
                'question_type': 'priority_based',
                'options': [
                    "Less than 500 sq ft",
                    "500 - 1000 sq ft",
                    "1000 - 1500 sq ft",
                    "1500 - 2000 sq ft",
                    "More than 2000 sq ft"
                ]
            },
            {
                'question_text': "Preferred Floor Level",
                'question_type': 'priority_based',
                'options': [
                    "Ground Floor",
                    "1-3",
                    "4-6",
                    "7+",
                    "No Preference"
                ]
            },
            {
                'question_text': "Preferred Room Location in Property",
                'question_type': 'priority_based',
                'options': [
                    "Center",
                    "Circumferential"
                ]
            },
            {
                'question_text': "Preferred Amenities",
                'question_type': 'multiple_mcq',
                'options': [
                    "Wi-Fi",
                    "Air Conditioning",
                    "Heating",
                    "Parking",
                    "Laundry Facilities",
                    "Swimming Pool",
                    "Gym",
                    "Pet-Friendly",
                    "Balcony",
                    "Elevator",
                    "Security Services",
                    "Other"
                ]
            },
            {
                'question_text': "Budget for Rent per Month",
                'question_type': 'priority_based',
                'options': [
                    "Below $500",
                    "$500 - $1000",
                    "$1000 - $1500",
                    "$1500 - $2000",
                    "Above $2000"
                ]
            },
            {
                'question_text': "Number of Beds Required",
                'question_type': 'priority_based',
                'options': [
                    "1 Bed",
                    "2 Beds",
                    "3 Beds",
                    "4+ Beds"
                ]
            },
            {
                'question_text': "Maximum Number of People Allowed",
                'question_type': 'priority_based',
                'options': [
                    "1-2",
                    "3-4",
                    "5-6",
                    "7+"
                ]
            },
            {
                'question_text': "Smoking Preference",
                'question_type': 'single_mcq',
                'options': [
                    "Non-smoker",
                    "Occasional Smoker (Outside Only)",
                    "Smoker (Allowed Inside Property)",
                    "No Preference"
                ]
            },
            {
                'question_text': "Alcohol Consumption Preference",
                'question_type': 'single_mcq',
                'options': [
                    "Non-drinker",
                    "Occasional Drinker (No Alcohol Inside Property)",
                    "Social Drinker (Alcohol Allowed Inside Property)",
                    "No Preference"
                ]
            },
            {
                'question_text': "Pet Ownership Preference",
                'question_type': 'priority_based',
                'options': [
                    "No Pets",
                    "Small Pets (e.g., Cats, Small Dogs, Fish)",
                    "Medium Pets (e.g., Medium-sized Dogs)",
                    "Large Pets (e.g., Large Dogs)",
                    "No Preference"
                ]
            },
            {
                'question_text': "Lease Duration Preference",
                'question_type': 'single_mcq',
                'options': [
                    "Short-term Stay (< 6 Months)",
                    "Medium-term Stay (6 Months to 1 Year)",
                    "Long-term Stay (1 to 3 Years)",
                    "Very Long-term Stay (> 3 Years)",
                    "No Preference"
                ]
            },
            {
                'question_text': "Availability Start Date",
                'question_type': 'single_mcq',
                'options': [
                    "As Soon as Possible",
                    "Within 1 Month",
                    "Within 3 Months",
                    "Other"
                ]
            },
        ]

        # Step 3: Add Tenant Preference Questions and Options
        for tq in tenant_questions:
            # Get question type instance
            qt = get_question_type(tq['question_type'])
            if not qt:
                continue  # Skip if question type not found

            # Create or get the question
            question, created = TenantPreferenceQuestionModel.objects.get_or_create(
                question_text=tq['question_text'],
                question_type=qt,
                defaults={
                    'is_active': True,
                    'is_deleted': False,
                    'created_at': now()
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Question: {question.question_text}"))
            else:
                self.stdout.write(f"Question already exists: {question.question_text}")

            # Add options to the question
            for option_text in tq['options']:
                option, opt_created = TenantPreferenceOptionModel.objects.get_or_create(
                    question=question,
                    option_text=option_text,
                    defaults={
                        'is_active': True,
                        'is_deleted': False,
                        'created_at': now()
                    }
                )
                if opt_created:
                    self.stdout.write(self.style.SUCCESS(f"  - Added Option: {option.option_text}"))
                else:
                    self.stdout.write(f"  - Option already exists: {option.option_text}")

        self.stdout.write(self.style.SUCCESS("Tenant preference questions and options have been successfully added."))
