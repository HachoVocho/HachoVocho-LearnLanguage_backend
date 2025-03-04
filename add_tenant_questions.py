# tenant_questions.py

from django.utils.timezone import now
from tenant.models import (
    TenantPreferenceQuestionTypeModel,
    TenantPreferenceQuestionModel,
    TenantPreferenceOptionModel
)

def add_tenant_preference_questions():
    # Step 1: Define Question Types

    # Step 2: Define Tenant Preference Questions
    tenant_questions = [
        {
            'question_text': "Which country are you from?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "United States",
                "Canada",
                "United Kingdom",
                "Australia",
                "Germany",
                "India",
                "China",
                "Japan",
                "Other"
            ]
        },
        {
            'question_text': "What is your religion? (Select all that apply)",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Christianity",
                "Islam",
                "Hinduism",
                "Buddhism",
                "Judaism",
                "Sikhism",
                "No Preference",
                "Other"
            ]
        },
        {
            'question_text': "What is your current occupation?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Student",
                "Working Professional",
                "Business Owner",
                "Retiree",
                "Freelancer/Remote Worker",
                "Other"
            ]
        },
        {
            'question_text': "What is your annual income range?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Two-Figure Income (< $100/year)",
                "Three-Figure Income ($100 - $999/year)",
                "Four-Figure Income ($1,000 - $9,999/year)",
                "Five-Figure Income ($10,000 - $99,999/year)",
                "Six-Figure Income ($100,000+/year)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "Do you smoke?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Non-smoker",
                "Occasional Smoker (Outside Only)",
                "Smoker (Allowed Inside Property)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "Do you consume alcohol?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Non-drinker",
                "Occasional Drinker (No Alcohol Inside Property)",
                "Social Drinker (Alcohol Allowed Inside Property)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "How would you describe your socializing attitude?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Introverted (Prefer Keeping to Themselves)",
                "Balanced (Friendly but Respect Privacy)",
                "Extroverted (Enjoy Socializing and Community Activities)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "What is your marital status?",
            'question_type': TenantPreferenceQuestionTypeModel(type_name='Single Choice MCQ'),
            'options': [
                "Single",
                "Married Without Children",
                "Married With Children",
                "Divorced/Separated",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "What are your dietary habits?",
            'question_type': 'single_mcq',
            'options': [
                "Vegetarian",
                "Vegan",
                "Non-vegetarian (No Restrictions)",
                "Non-vegetarian (No Beef/Pork)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "Do you own any pets?",
            'question_type': 'single_mcq',
            'options': [
                "No Pets",
                "Small Pets (e.g., Cats, Small Dogs, Fish)",
                "Medium Pets (e.g., Medium-sized Dogs)",
                "Large Pets (e.g., Large Dogs)",
                "Prefer Not to Disclose"
            ]
        },
        {
            'question_text': "What is your intended stay duration?",
            'question_type': 'single_mcq',
            'options': [
                "Short-term Stay (< 6 Months)",
                "Medium-term Stay (6 Months to 1 Year)",
                "Long-term Stay (1 to 3 Years)",
                "Very Long-term Stay (> 3 Years)",
                "Prefer Not to Disclose"
            ]
        }
    ]

    # Step 3: Add Tenant Preference Questions and Options
    for tq in tenant_questions:
        # Get question type instance
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
            print(f"Created Question: {question.question_text}")
        else:
            print(f"Question already exists: {question.question_text}")

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
                print(f"  - Added Option: {option.option_text}")
            else:
                print(f"  - Option already exists: {option.option_text}")

    print("Tenant preference questions and options have been successfully added.")

if __name__ == "__main__":
    add_tenant_preference_questions()
