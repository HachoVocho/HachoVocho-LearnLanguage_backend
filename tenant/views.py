from datetime import datetime
import os
from django.forms import ValidationError
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
# At the top of your views.py
from django.db.models import Prefetch  # Add this import
from landlord.models import LandlordDetailsModel, LandlordPropertyRoomDetailsModel, LandlordRoomWiseBedModel
from payments.models import TenantPaymentModel
from translation_utils import DEFAULT_LANGUAGE_CODE, get_translation
from translations.models import LanguageModel
from .serializers import PropertyDetailRequestSerializer
from localization.models import CityModel, CountryModel
from .serializers import AddIdentityDocumentSerializer, TenantDocumentTypeSerializer, TenantIdentityDocumentSerializer, TenantIdentityDocumentUpdateSerializer, TenantPreferenceAnswerSerializer, TenantPreferenceQuestionsAnswersRequestSerializer, TenantProfileRequestSerializer, TenantQuestionSerializer, TenantSignupSerializer
from response import Response as ResponseData
from .models import TenantDetailsModel, TenantDocumentTypeModel, TenantEmailVerificationModel, TenantIdentityVerificationFile, TenantIdentityVerificationModel, TenantPersonalityDetailsModel, TenantPreferenceAnswerModel, TenantPreferenceOptionModel, TenantPreferenceQuestionModel
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
import random
from landlord.models import LandlordPropertyDetailsModel, LandlordPropertyMediaModel
from .serializers import PropertyListRequestSerializer
from .models import (
    TenantDetailsModel,
    TenantPersonalityDetailsModel,
    OccupationModel,
    ReligionModel,
    IncomeRangeModel,
    SmokingHabitModel,
    DrinkingHabitModel,
    SocializingHabitModel,
    RelationshipStatusModel,
    FoodHabitModel,
)

from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    Returns distance in kilometers rounded to two decimal places.
    """
    R = 6371  # Radius of Earth in km

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(R * c, 2)  # Distance in km, rounded to 2 decimal places


@api_view(["POST"])
def tenant_signup(request):
    """API to handle tenant signup"""
    try:
        print(request.data)
        serializer = TenantSignupSerializer(data=request.data)
        # Validate incoming data
        if serializer.is_valid():
            # Get the language code from request (if provided) for translation lookup
            language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
            if not language_code:
                language_code = DEFAULT_LANGUAGE_CODE
            email = serializer.validated_data['email']
            # First check if the email exists for a landlord
            landlord = LandlordDetailsModel.objects.filter(email=email, is_active=True).first()
            if landlord is not None:
                message = get_translation("ERR_EMAIL_EXISTS_FOR_LANDLORD", language_code)
                return Response(
                    ResponseData.error(message),
                    status=status.HTTP_200_OK
                )
            tenant = TenantDetailsModel.objects.filter(email=email).first()

            # Try to get language for the tenant from the request if provided
            preferred_language = None
            try:
                preferred_language = LanguageModel.objects.get(code=language_code)
            except LanguageModel.DoesNotExist:
                preferred_language = None

            # If the tenant exists but is not active
            if tenant is not None and tenant.is_active is False:
                # Check for existing, unverified OTP
                tenant_verification = TenantEmailVerificationModel.objects.filter(
                    tenant=tenant,
                    is_verified=False
                ).first()
                otp = str(random.randint(100000, 999999))  # Generate OTP
                if tenant_verification:
                    # Generate a new OTP and send email
                    tenant_verification.otp = otp
                    tenant_verification.created_at = now()
                    tenant_verification.save()
                    send_otp_email(tenant.email, otp)
                else:
                    # No unverified OTP exists; create a new verification entry
                    TenantEmailVerificationModel.objects.create(
                        tenant=tenant,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(tenant.email, otp)
                message = get_translation("SUCC_TENANT_OTP_SENT", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )
            elif tenant is not None and tenant.is_active is True:
                message = get_translation("ERR_EMAIL_EXISTS", language_code)
                return Response(
                    ResponseData.error(message),
                    status=status.HTTP_200_OK
                )
            else:
                # If the tenant doesn't exist, create a new tenant
                validated_data = serializer.validated_data
                print(f"validated_data {validated_data}")
                if validated_data['password'] != '':
                    validated_data['password'] = make_password(validated_data['password'])
                    # If a preferred language is found, add it to the data
                    if preferred_language:
                        validated_data['preferred_language'] = preferred_language
                    tenant = TenantDetailsModel.objects.create(**validated_data)
                    # Generate OTP for the new tenant
                    otp = str(random.randint(100000, 999999))
                    TenantEmailVerificationModel.objects.create(
                        tenant=tenant,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(tenant.email, otp)
                    message = get_translation("SUCC_TENANT_SIGNUP_VERIFY", language_code)
                    return Response(
                        ResponseData.success(tenant.id, message),
                        status=status.HTTP_201_CREATED
                    )
                else:
                    # If no password is provided, create tenant as active directly.
                    if preferred_language:
                        validated_data['preferred_language'] = preferred_language
                    tenant = TenantDetailsModel.objects.create(**validated_data, is_active=True)
                    message = get_translation("SUCC_TENANT_SIGNUP", language_code)
                    return Response(
                        ResponseData.success(tenant.id, message),
                        status=status.HTTP_201_CREATED
                    )
        # If the serializer validation fails, return errors
        error_message = " ".join(
            [f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()]
        )
        return Response(
            ResponseData.error(error_message),
            status=status.HTTP_409_CONFLICT
        )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def send_otp_email(email, otp):
    """Helper function to send OTP email"""
    try:
        send_mail(
            subject='Verify Your Email',
            message=f'Your OTP for email verification is: {otp}',
            from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
            recipient_list=[email],
            fail_silently=False,  # Raise error if email fails
        )
    except Exception as e:
        raise ValidationError(f"Failed to send email: {str(e)}")
    
@api_view(["POST"])
def save_tenant_preferences(request):
    """
    API to save or update tenant preferences into the database.
    """
    serializer = TenantPreferenceAnswerSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    user_id = data['user_id']
    answers = data['answers']

    # Validate tenant existence
    tenant = TenantDetailsModel.objects.filter(id=user_id, is_active=True).first()
    if not tenant:
        return Response(
            ResponseData.error('Invalid tenant ID or tenant is not active.'),
            status=status.HTTP_400_BAD_REQUEST
        )
    print(f'answersvvv {answers}')
    for answer in answers:
        question_id = answer.get("question_id")
        selected_answers = answer.get("answers")

        # Validate question existence
        question = TenantPreferenceQuestionModel.objects.filter(id=question_id).first()
        if not question:
            return Response(
                ResponseData.error(f"Invalid question ID: {question_id}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        existing_answers = TenantPreferenceAnswerModel.objects.filter(
            tenant=tenant,
            question=question
        )
        selected_option_ids = [opt if isinstance(opt, int) else opt.get("option_id") for opt in selected_answers]
        options_to_remove = existing_answers.exclude(option_id__in=selected_option_ids)
        print(f'options_to_removevv {options_to_remove}')
        options_to_remove.delete()
        # Process each selected answer
        for selected_answer in selected_answers:
            if isinstance(selected_answer, dict):
                # Priority-based answers
                option_id = selected_answer.get("option_id")
                priority = selected_answer.get("priority")
                # Validate option existence
                option = TenantPreferenceOptionModel.objects.filter(id=option_id, question=question).first()
                if not option:
                    return Response(
                        ResponseData.error(f"Invalid option ID: {option_id} for question ID: {question_id}"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Check if an answer already exists
                preference_answer, created = TenantPreferenceAnswerModel.objects.update_or_create(
                    tenant=tenant,
                    question=question,
                    option=option,
                    defaults={"priority": priority}
                )

            else:
                # Single or Multiple choice answers
                option_id = selected_answer

                # Validate option existence
                option = TenantPreferenceOptionModel.objects.filter(id=option_id, question=question).first()
                if not option:
                    return Response(
                        ResponseData.error(f"Invalid option ID: {option_id} for question ID: {question_id}"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Check if an answer already exists
                preference_answer, created = TenantPreferenceAnswerModel.objects.update_or_create(
                    tenant=tenant,
                    question=question,
                    option=option,
                    defaults={"priority": None}  # Single/Multiple choice doesn't have priority
                )

    return Response(
        ResponseData.success_without_data("Tenant preferences saved/updated successfully."),
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
def get_tenant_preference_questions_answers(request):
    """
    API to fetch all tenant preference questions along with their answers (if any).
    Expects a POST request with 'user_id' in the request data.
    """
    # Step 1: Validate the incoming request data
    serializer = TenantPreferenceQuestionsAnswersRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_id = serializer.validated_data.get('user_id')
    
    # Step 2: Fetch the tenant based on user_id
    tenant = TenantDetailsModel.objects.filter(id=user_id, is_active=True).first()
    if not tenant:
        return Response(
            ResponseData.error("Invalid tenant ID or tenant is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 3: Fetch all active and non-deleted tenant preference questions with related types and options
    questions = TenantPreferenceQuestionModel.objects.filter(
        is_active=True, 
        is_deleted=False
    ).select_related('question_type').prefetch_related('question_options')
    
    # Step 4: Prepare the response data
    data = []
    for question in questions:
        # Initialize question data structure without options yet
        question_data = {
            'id': question.id,
            'question_text': question.question_text,
            'question_type': {
                'id': question.question_type.id,
                'type_name': question.question_type.type_name,
                'description': question.question_type.description
            }
        }
        
        # Fetch answers for this question by the tenant, if any
        answers = TenantPreferenceAnswerModel.objects.filter(
            tenant=tenant,
            question=question,
            is_active=True,
            is_deleted=False
        ).order_by('priority')
        
        # Build a list of selected option IDs based on the question type.
        selected_option_ids = []
        if answers.exists():
            if question.question_type.type_name in ['single_mcq', 'multiple_mcq', 'priority_based']:
                selected_option_ids = [answer.option.id for answer in answers]
        
        # Separate the question options into selected and unselected lists.
        selected_options = []
        unselected_options = []
        for option in question.question_options.all():
            option_data = {
                'id': option.id,
                'option_text': option.option_text
            }
            if option.id in selected_option_ids:
                selected_options.append(option_data)
            else:
                unselected_options.append(option_data)
        
        # Add the separated lists into the question data.
        question_data['selected_options'] = selected_options
        question_data['unselected_options'] = unselected_options
        
        # Optionally, include raw answer data if needed:
        if answers.exists():
            if question.question_type.type_name in ['single_mcq', 'multiple_mcq']:
                question_data['answers'] = selected_option_ids
            elif question.question_type.type_name == 'priority_based':
                question_data['answers'] = [
                    {
                        'option_id': answer.option.id,
                        'priority': answer.priority
                    } for answer in answers
                ]
        
        data.append(question_data)
    
    # Step 5: Return the response
    return Response(
        ResponseData.success(data, "Tenant preferences fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
def get_tenant_profile_details(request):
    """
    API to fetch tenant profile details along with personality details.
    Expects a POST request with 'user_id' in the request data.
    Additionally returns dropdown options for personality fields and identity verification data.
    For each dropdown, an 'is_selected' flag is included.
    Also provides profile completion percentage and personality completion percentage,
    plus a basic suggestion on required identity documents based on occupation.
    """
    # Step 1: Validate request data
    print(request.data)
    serializer = TenantProfileRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_id = serializer.validated_data.get("user_id")
    
    # Step 2: Fetch tenant
    tenant = TenantDetailsModel.objects.filter(id=user_id, is_active=True, is_deleted=False).first()
    if not tenant:
        return Response(
            ResponseData.error("Invalid tenant ID or tenant is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 3: Build tenant basic profile data
    tenant_data = {
        "id": tenant.id,
        "first_name": tenant.first_name,
        "last_name": tenant.last_name,
        "email": tenant.email,
        "phone_number": tenant.phone_number,
        "date_of_birth": tenant.date_of_birth.strftime("%Y-%m-%d") if tenant.date_of_birth else None,
        "profile_picture": tenant.profile_picture.url if tenant.profile_picture else None,
    }
    
    # Step 4: Fetch personality details (if exists) with null checks
    personality = TenantPersonalityDetailsModel.objects.filter(
        tenant=tenant, is_active=True, is_deleted=False
    ).first()
    
    if personality:
        personality_data = {
            "occupation": {
                "id": personality.occupation.id if personality.occupation else None,
                "title": personality.occupation.title if personality.occupation else None
            },
            "country": {
                "id": personality.country.id if personality.country else None,
                "title": getattr(personality.country, 'title', None) or getattr(personality.country, 'name', None)
            },
            "religion": {
                "id": personality.religion.id if personality.religion else None,
                "title": personality.religion.title if personality.religion else None
            },
            "income_range": {
                "id": personality.income_range.id if personality.income_range else None,
                "title": personality.income_range.title if personality.income_range else None,
                "min_income": personality.income_range.min_income if personality.income_range else None,
                "max_income": personality.income_range.max_income if personality.income_range else None,
            },
            "smoking_habit": {
                "id": personality.smoking_habit.id if personality.smoking_habit else None,
                "title": personality.smoking_habit.title if personality.smoking_habit else None
            },
            "drinking_habit": {
                "id": personality.drinking_habit.id if personality.drinking_habit else None,
                "title": personality.drinking_habit.title if personality.drinking_habit else None
            },
            "socializing_habit": {
                "id": personality.socializing_habit.id if personality.socializing_habit else None,
                "title": personality.socializing_habit.title if personality.socializing_habit else None
            },
            "relationship_status": {
                "id": personality.relationship_status.id if personality.relationship_status else None,
                "title": personality.relationship_status.title if personality.relationship_status else None
            },
            "food_habit": {
                "id": personality.food_habit.id if personality.food_habit else None,
                "title": personality.food_habit.title if personality.food_habit else None
            },
            "pet_lover": personality.pet_lover,
            "created_at": personality.created_at.strftime("%Y-%m-%d %H:%M:%S") if personality.created_at else None,
        }
    else:
        personality_data = None

    # Step 5: Build dropdown options with selection flags
    def get_options(queryset, key='title', selected_id=None):
        return [
            {
                "id": obj.id,
                "title": getattr(obj, key, None),
                "is_selected": (obj.id == selected_id)
            }
            for obj in queryset.filter(is_active=True, is_deleted=False)
        ]
    
    occupations = get_options(
        OccupationModel.objects, 
        key='title', 
        selected_id=personality.occupation.id if personality and personality.occupation else None
    )
    religions = get_options(
        ReligionModel.objects, 
        key='title', 
        selected_id=personality.religion.id if personality and personality.religion else None
    )
    income_ranges = get_options(
        IncomeRangeModel.objects, 
        key='title', 
        selected_id=personality.income_range.id if personality and personality.income_range else None
    )
    smoking_habits = get_options(
        SmokingHabitModel.objects, 
        key='title', 
        selected_id=personality.smoking_habit.id if personality and personality.smoking_habit else None
    )
    drinking_habits = get_options(
        DrinkingHabitModel.objects, 
        key='title', 
        selected_id=personality.drinking_habit.id if personality and personality.drinking_habit else None
    )
    socializing_habits = get_options(
        SocializingHabitModel.objects, 
        key='title', 
        selected_id=personality.socializing_habit.id if personality and personality.socializing_habit else None
    )
    relationship_statuses = get_options(
        RelationshipStatusModel.objects, 
        key='title', 
        selected_id=personality.relationship_status.id if personality and personality.relationship_status else None
    )
    food_habits = get_options(
        FoodHabitModel.objects, 
        key='title', 
        selected_id=personality.food_habit.id if personality and personality.food_habit else None
    )

    document_types = TenantDocumentTypeModel.objects.filter(is_active=True, is_deleted=False)
    document_types_data = [
        {
            "id": dt.id,
            "type_name": dt.type_name,
            "description": dt.description
        }
        for dt in document_types
    ]

    # Step 6: Calculate profile completion
    # Out of 7 fields, 4 are always filled (first_name, last_name, email, password) => we only check phone_number, date_of_birth, profile_picture
    total_profile_fields = 3
    filled_profile = 0
    if tenant.phone_number: filled_profile += 1
    if tenant.date_of_birth: filled_profile += 1
    if tenant.profile_picture: filled_profile += 1
    profile_completion = int((filled_profile / total_profile_fields) * 100)

    # Step 7: Calculate personality completion (10 fields)
    # occupation, country, religion, income_range, smoking_habit, drinking_habit,
    # socializing_habit, relationship_status, food_habit, pet_lover
    total_personality_fields = 10
    filled_personality = 0
    if personality and personality.occupation: filled_personality += 1
    if personality and personality.country: filled_personality += 1
    if personality and personality.religion: filled_personality += 1
    if personality and personality.income_range: filled_personality += 1
    if personality and personality.smoking_habit: filled_personality += 1
    if personality and personality.drinking_habit: filled_personality += 1
    if personality and personality.socializing_habit: filled_personality += 1
    if personality and personality.relationship_status: filled_personality += 1
    if personality and personality.food_habit: filled_personality += 1
    #if personality and personality.pet_lover: filled_personality += 1
    personality_completion = int((filled_personality / total_personality_fields) * 100)

    # Step 8: Basic logic to suggest which document is needed based on occupation title
    required_documents = []
    occupant_title = (personality.occupation.title.lower() if personality and personality.occupation else '') if personality else ''
    if "student" in occupant_title:
        required_documents.append("Student ID")
    elif "employee" in occupant_title or "work" in occupant_title:
        required_documents.append("Work ID")
    else:
        required_documents.append("Any Government ID")

    # Step 9: Prepare full response data
    data = {
        "tenant": tenant_data,
        "personality_details": personality_data,
        "dropdown_options": {
            "occupations": occupations,
            "religions": religions,
            "income_ranges": income_ranges,
            "smoking_habits": smoking_habits,
            "drinking_habits": drinking_habits,
            "socializing_habits": socializing_habits,
            "relationship_statuses": relationship_statuses,
            "food_habits": food_habits,
        },
        "profile_completion": profile_completion,
        "personality_completion": personality_completion,
        "required_identity_documents": required_documents,
    }
    print(f'profile_completion {profile_completion}')
    print(f'personality_completion {personality_completion}')
    print(f'required_identity_documents {required_documents}')
    return Response(
        ResponseData.success(data, "Tenant profile fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
def add_identity_document(request):
    print(f'request.data {request.data}')
    serializer = AddIdentityDocumentSerializer(data=request.data)
    if serializer.is_valid():
        tenant_id = serializer.validated_data['tenant_id']
        document_type_id = serializer.validated_data['document_type']
        document_number = serializer.validated_data.get('document_number', '')
        files = request.FILES.getlist('document_files')
        # Create a new identity document record
        identity_doc = TenantIdentityVerificationModel.objects.create(
            tenant_id=tenant_id,
            document_type_id=document_type_id,
            document_number=document_number,
            submitted_at=now(),
            verification_status='pending'
        )
        # Create file records for each file uploaded
        for file in files:
            TenantIdentityVerificationFile.objects.create(
                identity_document=identity_doc,
                file=file,
                uploaded_at=now()
            )
        output_serializer = TenantIdentityDocumentSerializer(identity_doc, context={'request': request})
        return Response(
            ResponseData.success(output_serializer.data, "Identity document added successfully."),
            status=status.HTTP_201_CREATED
        )
    return Response(ResponseData.error(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def get_all_identity_documents(request):
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            ResponseData.error("tenant_id parameter is required."),
            status=status.HTTP_400_BAD_REQUEST
        )
    documents = TenantIdentityVerificationModel.objects.filter(
        tenant_id=tenant_id, is_active=True, is_deleted=False
    )
    document_serializer = TenantIdentityDocumentSerializer(
        documents, many=True, context={'request': request}
    )
    
    document_types = TenantDocumentTypeModel.objects.filter(is_active=True, is_deleted=False)
    doc_types_serializer = TenantDocumentTypeSerializer(
        document_types, many=True, context={'request': request}
    )
    
    data = {
        "documents": document_serializer.data,
        "document_types": doc_types_serializer.data,
    }
    
    return Response(
        ResponseData.success(data, "Identity documents fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def update_identity_document(request):
    """
    API to update an existing identity document.
    Updates only the fields present in request.data.
    """
    doc_id = request.data.get('document_id')
    if not doc_id:
        return Response(ResponseData.error("Document id is required."), status=status.HTTP_400_BAD_REQUEST)

    try:
        document = TenantIdentityVerificationModel.objects.get(id=doc_id, is_active=True, is_deleted=False)
    except TenantIdentityVerificationModel.DoesNotExist:
        return Response(ResponseData.error("Document not found."), status=status.HTTP_404_NOT_FOUND)

    # Extract request data
    document_type_id = request.data.get('document_type')
    document_number = request.data.get('document_number')
    # Ensure document_number uniqueness check is bypassed for the same document
    if document_number and document_number != document.document_number:
        if TenantIdentityVerificationModel.objects.filter(document_number=document_number).exclude(id=doc_id).exists():
            return Response(ResponseData.error("Document number already exists."), status=status.HTTP_400_BAD_REQUEST)

    # Update only fields that are present in the request
    if document_type_id:
        try:
            document_type = TenantDocumentTypeModel.objects.get(id=document_type_id)
            document.document_type = document_type
        except TenantDocumentTypeModel.DoesNotExist:
            return Response(ResponseData.error("Invalid document type."), status=status.HTTP_400_BAD_REQUEST)

    if document_number:
        document.document_number = document_number
        document.verification_status = 'pending'

    document.save()

    # Handle file uploads if new files are provided
    # Fetch existing files from the TenantIdentityVerificationFile table
    existing_files = TenantIdentityVerificationFile.objects.filter(identity_document=document)

    # Create a set of existing file names
    existing_file_names = {os.path.basename(file_obj.file.name) for file_obj in existing_files}

    # Get new uploaded files
    new_files = request.FILES.getlist('document_files')

    # Convert new file names into a set for comparison
    new_file_names = {file.name for file in new_files}

    # Identify files to delete (existing files not present in new uploads)
    files_to_delete = existing_files.exclude(file__in=[f'static/tenant_identity_documents/{name}' for name in new_file_names])

    # Delete missing files from the database and storage
    for file_obj in files_to_delete:
        
        # Delete from file system
        os.remove(file_obj.file.name)
        
        # Delete from database
        file_obj.delete()

    # Add only new files (avoid re-adding existing ones)
    for file in new_files:
        if file.name not in existing_file_names:
            TenantIdentityVerificationFile.objects.create(
                identity_document=document,
                file=file,
                uploaded_at=now()
            )


    return Response(ResponseData.success_without_data("Identity document updated successfully."), status=status.HTTP_200_OK)

@api_view(["DELETE"])
def delete_identity_document(request):
    doc_id = request.data.get('id')
    if not doc_id:
        return Response(ResponseData.error("Document id is required."), status=status.HTTP_400_BAD_REQUEST)
    try:
        document = TenantIdentityVerificationModel.objects.get(id=doc_id, is_active=True, is_deleted=False)
    except TenantIdentityVerificationModel.DoesNotExist:
        return Response(ResponseData.error("Document not found."), status=status.HTTP_404_NOT_FOUND)
    document.is_deleted = True
    document.deleted_at = now()
    document.save()
    return Response(ResponseData.success_without_data("Identity document deleted successfully."), status=status.HTTP_200_OK)

@api_view(["POST"])
def update_tenant_profile_details(request):
    print(request.data)
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            ResponseData.error("Tenant id is required."),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_deleted=False)
    except TenantDetailsModel.DoesNotExist:
        return Response(
            ResponseData.error("Tenant not found."),
            status=status.HTTP_404_NOT_FOUND
        )

    # Handle profile picture update
    if 'profile_picture' in request.FILES:
        # Delete existing profile picture
        if tenant.profile_picture:
            old_path = tenant.profile_picture.path
            if os.path.exists(old_path):
                os.remove(old_path)
        tenant.profile_picture = request.FILES['profile_picture']

    # Update other fields
    if 'date_of_birth' in request.data:
        tenant.date_of_birth = request.data['date_of_birth']
    if 'phone_number' in request.data:
        tenant.phone_number = request.data['phone_number']

    tenant.save()

    return Response(
        ResponseData.success_without_data("Tenant profile updated successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def update_tenant_personality(request):
    print(f'request.data {request.data}')
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            ResponseData.error("Tenant id is required."), 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_deleted=False)
    except TenantDetailsModel.DoesNotExist:
        return Response(
            ResponseData.error("Tenant not found."),
            status=status.HTTP_404_NOT_FOUND
        )

    personality, created = TenantPersonalityDetailsModel.objects.get_or_create(
        tenant=tenant,
        defaults={'tenant': tenant}
    )

    # Update fields
    field_map = {
        'occupation_id': (OccupationModel, 'occupation'),
        'country_id': (CountryModel, 'country'),
        'religion_id': (ReligionModel, 'religion'),
        'income_range_id': (IncomeRangeModel, 'income_range'),
        'smoking_habit_id': (SmokingHabitModel, 'smoking_habit'),
        'drinking_habit_id': (DrinkingHabitModel, 'drinking_habit'),
        'socializing_habit_id': (SocializingHabitModel, 'socializing_habit'),
        'relationship_status_id': (RelationshipStatusModel, 'relationship_status'),
        'food_habit_id': (FoodHabitModel, 'food_habit'),
        'pet_lover': (False, 'pet_lover')
    }

    for field, (model, field_name) in field_map.items():
        if field in request.data:
            if model:
                try:
                    obj = model.objects.get(id=request.data[field])
                    setattr(personality, field_name, obj)
                except model.DoesNotExist:
                    pass
            else:
                setattr(personality, field_name, request.data[field])

    personality.save()

    return Response(
        ResponseData.success_without_data("Personality details updated successfully."),
        status=status.HTTP_200_OK
    )


# views.py

@api_view(["POST"])
def get_properties_by_city_overview(request):
    """
    API to fetch high-level properties in a specific city with all media combined.
    """
    print(f'request.data {request.data}')
    serializer = PropertyListRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error("Validation error", serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    city_id = serializer.validated_data['city_id']
    tenant_id = serializer.validated_data['tenant_id']
    # Get city object
    city_obj = CityModel.objects.filter(id=city_id).select_related('state__country').first()

    # Fetch currency symbol
    currency_symbol = city_obj.state.country.currency_symbol if city_obj and city_obj.state and city_obj.state.country else None

    # Update tenant's preferred city
    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True)
        tenant.preferred_city_id = city_id
        tenant.save()
    except TenantDetailsModel.DoesNotExist:
        return Response(
            ResponseData.error("Tenant not found"),
            status=status.HTTP_404_NOT_FOUND
        )

    # Get city name
    city_obj = CityModel.objects.filter(id=city_id).first()
    city_name = city_obj.name if city_obj else None

    # Filter properties
    properties = (
        LandlordPropertyDetailsModel.objects
        .filter(property_city_id=city_id, is_active=True, is_deleted=False)
        .select_related('property_type', 'property_city')
        .prefetch_related(
            'amenities',
            'property_media',
            Prefetch(
                'rooms',
                queryset=LandlordPropertyRoomDetailsModel.objects.filter(
                    is_active=True, 
                    is_deleted=False
                ).select_related('room_type').prefetch_related(
                    'room_media',
                    Prefetch(
                        'beds',
                        queryset=LandlordRoomWiseBedModel.objects.filter(
                            is_active=True,
                            is_deleted=False,
                            availability_start_date__isnull=False  # ✅ Only beds with availability date
                        ).prefetch_related('bed_media')
                    )
                )
            )
        )
    )

    property_list = []
    print(f'properties123 {properties}')
    landlord_id = -1
    for prop in properties:
        all_media = []
        landlord_id = prop.landlord.id
        # Property-level media
        all_media.extend([
            {"url": media.file.url, "type": media.media_type}
            for media in prop.property_media.filter(is_active=True)
        ])

        # Amenities
        amenities = [
            amenity.name for amenity in prop.amenities.filter(is_active=True)
        ]

        available_beds = []  # ✅ Store bed details

        # Collect room + bed media in one list
        for room in prop.rooms.all():
            # Room media
            print(f'room123 {room}')
            all_media.extend([
                {"url": rm.file.url, "type": rm.media_type}
                for rm in room.room_media.filter(is_active=True)
            ])

            # Determine if the room is **Private** or **Sharing**
            room_type = room.room_type.type_name

            # Iterate through beds inside the room
            for bed in room.beds.all():
                if bed.availability_start_date:  # ✅ Only process beds with availability_start_date
                    # Convert date format
                    start_date_str = datetime.strftime(bed.availability_start_date, "%d %b %y")  # Example: 5th Feb 25


                    all_media.extend([
                        {"url": bm.file.url, "type": bm.media_type}
                        for bm in bed.bed_media.filter(is_active=True)
                    ])

                    # ✅ Add bed details to the list
                    available_beds.append({
                        "bed_id": bed.id,
                        "bed_number": bed.bed_number,
                        "room_type": room_type,
                        "rent_amount": str(bed.rent_amount) + f' {currency_symbol}',
                        "availability_start_date": start_date_str,
                        "is_rent_monthly": bed.is_rent_monthly,
                    })

        property_data = {
            "id": prop.id,
            "property_name": prop.property_name,
            "distance_from_city_center": haversine_distance(
                float(prop.latitude),
                float(prop.longitude),
                float(city_obj.latitude),
                float(city_obj.longitude)
            ),
            "property_size": prop.property_size,
            "property_type": prop.property_type.type_name if prop.property_type else None,
            "property_city": prop.property_city.name if prop.property_city else None,
            "number_of_rooms": prop.number_of_rooms,
            "floor": prop.floor,
            "property_description": prop.property_description,
            "amenities": amenities,
            "media": all_media,  # ✅ All media (property + rooms + beds)
            "available_beds": available_beds,  # ✅ List of available beds with details
        }
        if len(available_beds) != 0:
            property_list.append(property_data)

    data = {
        "preferred_city_name": city_name,
        "landlord_id" : landlord_id,
        "properties": property_list
    }
    return Response(
        ResponseData.success(data, "Properties fetched successfully"),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
def get_property_details(request):
    """
    2) API to fetch detailed property info (rooms & beds).
       Request: {'property_id': int}
       ResponseData.success({
         "id": ...,
         "property_name": ...,
         "property_address": ...,
         "property_size": ...,
         "property_type": ...,
         "property_city": ...,
         "pin_code": ...,
         "floor": ...,
         "property_description": ...,
         "amenities": [...],
         "latitude": ...,
         "longitude": ...,
         "media": [...],
         "rooms": [
           {
             "room_id": ...,
             "room_type": ...,
             "room_size": ...,
             "number_of_beds": ...,
             "max_people_allowed": ...,
             "floor": ...,
             "location_in_property": ...,
             "room_media": [...],
             "beds": [
               {
                 "bed_id": ...,
                 "bed_number": ...,
                 "is_available": ...,
                 "rent_per_month": ...,
                 "availability_start_date": ...,
                 "availability_end_date": ...,
                 "bed_media": [...]
               },
               ...
             ]
           },
           ...
         ]
       }, "Property details fetched successfully")
    """
    print(f'request.data {request.data}')
    serializer = PropertyDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    property_id = serializer.validated_data['property_id']
    tenant_id = serializer.validated_data['tenant_id']

    # Fetch the property
    prop = (
        LandlordPropertyDetailsModel.objects
        .filter(id=property_id, is_active=True, is_deleted=False)
        .select_related('property_type', 'property_city')
        .prefetch_related(
            'amenities',
            'property_media',
            Prefetch(
                'rooms',
                queryset=LandlordPropertyRoomDetailsModel.objects.filter(
                    is_active=True, 
                    is_deleted=False
                ).prefetch_related(
                    'room_media',
                    Prefetch(
                        'beds',
                        queryset=LandlordRoomWiseBedModel.objects.filter(
                            is_active=True,
                            is_deleted=False
                        ).prefetch_related('bed_media')
                    )
                )
            )
        )
        .first()
    )

    if not prop:
        return Response(
            ResponseData.error("Property not found."),
            status=status.HTTP_404_NOT_FOUND
        )

    # Property media
    property_media = [
        {"url": media.file.url, "type": media.media_type}
        for media in prop.property_media.filter(is_active=True)
    ]

    # Amenities
    amenities = [
        amenity.name for amenity in prop.amenities.filter(is_active=True)
    ]
    # Fetch the tenant to check phone verification and payment status.
    tenant = TenantDetailsModel.objects.filter(id=tenant_id).first()
    is_phone_verified = bool(tenant and tenant.phone_number)
    payment = None
    is_payment_active = False
    if tenant:
        payment = TenantPaymentModel.objects.filter(
            tenant=tenant, is_active=True, is_deleted=False
        ).order_by('-paid_at').first()
        if payment and (payment.paid_at + timedelta(days=30) > now()):
            is_payment_active = True
    # Room details
    rooms_data = []
    for room in prop.rooms.all():
        room_media = [
            {"url": rm.file.url, "type": rm.media_type}
            for rm in room.room_media.filter(is_active=True)
        ]
        beds_data = []
        for bed in room.beds.all():
            bed_media = [
                {"url": bm.file.url, "type": bm.media_type}
                for bm in bed.bed_media.filter(is_active=True)
            ]
            start_date_str = ''
            if bed.availability_start_date is not None:
                start_date_str = datetime.strftime(bed.availability_start_date, "%d %b %y")
                beds_data.append({
                    "bed_id": bed.id,
                    "bed_number": bed.bed_number,
                    "is_available": bed.is_available,
                    "is_rent_monthly": bed.is_rent_monthly,
                    "min_agreement_duration_in_months": str(bed.min_agreement_duration_in_months),
                    "rent_amount": str(bed.rent_amount),
                    "availability_start_date": start_date_str,
                    "bed_media": bed_media,
              "is_phone_verified": is_phone_verified,
                "is_payment_active": is_payment_active,
                })

        rooms_data.append({
            "room_id": room.id,
            "room_type": room.room_type.type_name if room.room_type else None,
            "room_size": room.room_size,
            "number_of_beds": 1 if room.number_of_beds == None else room.number_of_beds,
            "max_people_allowed": 1 if room.max_people_allowed == None else room.max_people_allowed,
            "floor": 1 if room.floor == None else room.floor,
            "location_in_property": room.location_in_property,
            "room_media": room_media,
            "beds": beds_data
        })


    return Response(
        ResponseData.success(rooms_data, "Property details fetched successfully"),
        status=status.HTTP_200_OK
    )