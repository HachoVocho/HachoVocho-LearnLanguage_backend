from datetime import datetime
import os
import re
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from django.utils.translation import get_language
# At the top of your views.py
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch  # Add this import
from interest_requests.consumers import compute_personality_match
from landlord.models import LandlordBasePreferenceModel, LandlordDetailsModel, LandlordPropertyRoomDetailsModel, LandlordRoomWiseBedModel
from payments.models import TenantPaymentModel
from translation_utils import DEFAULT_LANGUAGE_CODE, get_translation
from translations.models import LanguageModel
from user.email_utils import send_otp_email
from .serializers import PropertyDetailRequestSerializer
from localization.models import CityModel, CountryModel
from .serializers import AddIdentityDocumentSerializer, TenantDocumentTypeSerializer, TenantIdentityDocumentSerializer, TenantIdentityDocumentUpdateSerializer, TenantPreferenceAnswerSerializer, TenantPreferenceQuestionsAnswersRequestSerializer, TenantProfileRequestSerializer, TenantQuestionSerializer, TenantSignupSerializer
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from .models import TenantDetailsModel, TenantDocumentTypeModel, TenantEmailVerificationModel, TenantIdentityVerificationFile, TenantIdentityVerificationModel, TenantPersonalityDetailsModel, TenantPreferenceAnswerModel, TenantPreferenceOptionModel, TenantPreferenceQuestionModel

from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
import random
from landlord.models import LandlordPropertyDetailsModel
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
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
                print(f'tenant.email {tenant.email} {otp}')
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
                    ResponseData.success(tenant_verification.tenant.id,message),
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
                    validated_data['is_google_account'] = True
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
    
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
    
    user_id = serializer.validated_data['user_id']
    
    # Step 2: Fetch the tenant based on user_id
    tenant = TenantDetailsModel.objects.filter(id=user_id, is_active=True).first()
    if not tenant:
        return Response(
            ResponseData.error("Invalid tenant ID or tenant is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Determine language codes
    lang = tenant.preferred_language.code   # e.g. "de"
    fallback = "en"
    
    # Step 3: Fetch questions with their translations and options+translations
    questions = (
        TenantPreferenceQuestionModel.objects
        .filter(is_active=True, is_deleted=False)
        .select_related('question_type')
        .prefetch_related(
            'translations',
            Prefetch(
                'options',
                queryset=TenantPreferenceOptionModel.objects.prefetch_related('translations')
            )
        )
    )
    
    # Step 4: Prepare the response data
    data = []
    for question in questions:
        # Pull the correct translation (or fallback)
        q_text = question.safe_translation_getter('title', language_code=lang, any_language=True) or ""
        
        question_data = {
            'id': question.id,
            'question_text': q_text,
            'question_type': {
                'id': question.question_type.id,
                'type_name': question.question_type.type_name,
                'description': question.question_type.description,
            },
        }
        
        # Fetch this tenant’s answers for the question
        answers = TenantPreferenceAnswerModel.objects.filter(
            tenant=tenant,
            question=question,
            is_active=True,
            is_deleted=False
        ).order_by('priority')
        
        selected_option_ids = [a.option_id for a in answers] if answers.exists() else []
        
        selected_options = []
        unselected_options = []
        for opt in question.options.all():
            o_text = opt.safe_translation_getter('text', language_code=lang, any_language=True) or ""
            opt_data = {'id': opt.id, 'option_text': o_text}
            
            if opt.id in selected_option_ids:
                selected_options.append(opt_data)
            else:
                unselected_options.append(opt_data)
        
        question_data['selected_options']   = selected_options
        question_data['unselected_options'] = unselected_options
        
        if answers.exists():
            tname = question.question_type.type_name
            if tname in ['single_mcq', 'multiple_mcq']:
                question_data['answers'] = selected_option_ids
            elif tname == 'priority_based':
                question_data['answers'] = [
                    {'option_id': a.option_id, 'priority': a.priority}
                    for a in answers
                ]
        
        data.append(question_data)
    
    # Step 5: Return the response
    return Response(
        ResponseData.success(data, "Tenant preferences fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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

    # determine language code (fall back to Django’s current or “en”)
    lang_code = (
        tenant.preferred_language.code
        if getattr(tenant, "preferred_language", None) and tenant.preferred_language.code
        else get_language() or "en"
    )

    try:
        currency_symbol = tenant.preferred_city.state.country.currency_symbol
    except (AttributeError, TenantDetailsModel.DoesNotExist):
        currency_symbol = ''

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

    # Step 4: Fetch personality details (if exists)
    personality = TenantPersonalityDetailsModel.objects.filter(
        tenant=tenant,
        is_active=True,
        is_deleted=False,
    ).first()

    if personality:
        personality_data = {
            "occupation": {
                "id": personality.occupation.id if personality.occupation else None,
                "title": personality.occupation.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.occupation else None
            },
            "country": {
                "id": personality.country.id if personality.country else None,
                "title": getattr(personality.country, 'title', None) or getattr(personality.country, 'name', None)
            },
            "religion": {
                "id": personality.religion.id if personality.religion else None,
                "title": personality.religion.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.religion else None
            },
            "income_range": {
                "id": personality.income_range.id if personality.income_range else None,
                "title": personality.income_range.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.income_range else None,
                "min_income": personality.income_range.min_income if personality.income_range else None,
                "max_income": personality.income_range.max_income if personality.income_range else None,
            },
            "smoking_habit": {
                "id": personality.smoking_habit.id if personality.smoking_habit else None,
                "title": personality.smoking_habit.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.smoking_habit else None
            },
            "drinking_habit": {
                "id": personality.drinking_habit.id if personality.drinking_habit else None,
                "title": personality.drinking_habit.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.drinking_habit else None
            },
            "socializing_habit": {
                "id": personality.socializing_habit.id if personality.socializing_habit else None,
                "title": personality.socializing_habit.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.socializing_habit else None
            },
            "relationship_status": {
                "id": personality.relationship_status.id if personality.relationship_status else None,
                "title": personality.relationship_status.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.relationship_status else None
            },
            "food_habit": {
                "id": personality.food_habit.id if personality.food_habit else None,
                "title": personality.food_habit.safe_translation_getter("title", language_code=lang_code, any_language=True)
                         if personality.food_habit else None
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
                "title": obj.safe_translation_getter(key, language_code=lang_code, any_language=True)
                         if hasattr(obj, "safe_translation_getter") else getattr(obj, key, None),
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
    countries = get_options(
        CountryModel.objects,
        key='name',
        selected_id=personality.country.id if personality and personality.country else None
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
    total_profile_fields = 3
    filled_profile = sum(bool(getattr(tenant, f)) for f in ['phone_number', 'date_of_birth', 'profile_picture'])
    profile_completion = int((filled_profile / total_profile_fields) * 100)

    # Step 7: Calculate personality completion
    total_personality_fields = 10
    if personality:
        total_personality_fields = 10
        filled_personality = sum(
            bool(getattr(personality, field))
            for field in [
                'occupation','country','religion','income_range',
                'smoking_habit','drinking_habit','socializing_habit',
                'relationship_status','food_habit','pet_lover'
            ]
        )
        personality_completion = int((filled_personality / total_personality_fields) * 100)
    else:
        personality_completion = 0
    # Step 8: Suggest required documents
    occ_title = (
        personality.occupation.safe_translation_getter("title", language_code=lang_code, any_language=True) or ""
    ).lower() if personality and personality.occupation else ""
    required_documents = []
    if "student" in occ_title:
        required_documents.append("Student ID")
    elif "employee" in occ_title or "work" in occ_title:
        required_documents.append("Work ID")
    else:
        required_documents.append("Any Government ID")

    # Step 9: Prepare full response data
    data = {
        "tenant": tenant_data,
        "personality_details": personality_data,
        "preferred_country_currency": currency_symbol,
        "dropdown_options": {
            "occupations": occupations,
            "religions": religions,
            "income_ranges": income_ranges,
            "smoking_habits": smoking_habits,
            "drinking_habits": drinking_habits,
            "socializing_habits": socializing_habits,
            "relationship_statuses": relationship_statuses,
            "food_habits": food_habits,
            "country": countries,
        },
        "profile_completion": profile_completion,
        "personality_completion": personality_completion,
        "required_identity_documents": required_documents,
    }

    return Response(
        ResponseData.success(data, "Tenant profile fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
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


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_properties_by_city_overview(request):
    """
    API to fetch property summaries in a city,
    sorted by tenant preference match (supports multi-select priority questions).
    """
    # 1. Validate input
    serializer = PropertyListRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors), status=400)
    city_id = serializer.validated_data['city_id']
    tenant_id = serializer.validated_data['tenant_id']

    # 2. Load city
    try:
        city_obj = CityModel.objects.select_related('state__country').get(id=city_id)
    except CityModel.DoesNotExist:
        return Response(ResponseData.success_without_data("City not found"), status=200)

    # 3. Load tenant & update preferred city
    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True)
    except TenantDetailsModel.DoesNotExist:
        return Response(ResponseData.error("Tenant not found"), status=404)
    tenant.preferred_city = city_obj
    tenant.save(update_fields=['preferred_city'])

    # 4. Load tenant personality
    try:
        tenant_persona = TenantPersonalityDetailsModel.objects.get(
            tenant=tenant, is_active=True, is_deleted=False
        )
    except TenantPersonalityDetailsModel.DoesNotExist:
        tenant_persona = None

    # 5. Fetch all tenant answers (multi-select supported)
    raw_answers = TenantPreferenceAnswerModel.objects.filter(
        tenant=tenant, is_active=True, is_deleted=False
    ).select_related('question', 'option')

    # Build map: question_text -> list of {value, priority}
    prefs = {}
    for ans in raw_answers:
        # pull translated option text (or any language fallback) instead of non‑existent .option_text
        text = ans.static_option or ans.option.safe_translation_getter(
            'text', language_code=tenant.preferred_language.code, any_language=True
        )
        # likewise pull the translated question text
        q_text = ans.question.safe_translation_getter(
            'text', language_code=tenant.preferred_language.code, any_language=True
        )
        prefs.setdefault(q_text, []).append({
            'value': text,
            'priority': ans.priority or 1
        })

    # Parsers
    def parse_numeric(val):
        m = re.search(r'\d+', val.replace(',', ''))
        return int(m.group()) if m else None

    def parse_range(val):
        nums = list(map(int, re.findall(r'\d+', val.replace(',', ''))))
        if len(nums) == 1:
            if 'Below' in val or '<' in val:
                return 0, nums[0]
            return nums[0], float('inf')
        if len(nums) >= 2:
            return nums[0], nums[1]
        return 0, float('inf')

    # 6. Load properties with prefetches
    country = city_obj.state.country
    currency_symbol = country.currency_symbol or ""
    currency = country.currency or ""

    props_qs = (
        LandlordPropertyDetailsModel.objects
        .filter(property_city=city_obj, is_active=True, is_deleted=False)
        .select_related('property_type', 'property_city')
        .prefetch_related(
            Prefetch(
                'rooms__beds',
                queryset=LandlordRoomWiseBedModel.objects.filter(
                    is_active=True, is_deleted=False,
                    availability_start_date__isnull=False
                ).prefetch_related('tenant_preference_answers'),
                to_attr='valid_beds'
            ),
            'property_media',
            'amenities'
        )
    )

    results = []
    last_landlord = None
    today = now().date()

    for prop in props_qs:
        last_landlord = prop.landlord_id

        # Gather rents, media, amenities
        monthly_rents, daily_rents = [], []
        media = [{"url": m.file.url, "type": m.media_type}
                 for m in prop.property_media.filter(is_active=True)]
        amenities = [a.name for a in prop.amenities.filter(is_active=True)]

        # Bed-level personality matching & collect beds data
        bed_scores, all_start_dates, all_min_durations = [], [], []
        max_people = None
        for room in prop.rooms.all():
            if room.max_people_allowed:
                max_people = room.max_people_allowed
            for bed in getattr(room, 'valid_beds', []):
                amt = float(bed.rent_amount)
                (monthly_rents if bed.is_rent_monthly else daily_rents).append(amt)
                all_start_dates.append(bed.availability_start_date)
                if bed.min_agreement_duration_in_months:
                    all_min_durations.append(bed.min_agreement_duration_in_months)
                answers = list(bed.tenant_preference_answers.all())
                if not answers:
                    base = LandlordBasePreferenceModel.objects.filter(landlord_id=prop.landlord_id).first()
                    if base:
                        answers = list(base.answers.all())
                match_pct, _ = compute_personality_match(tenant_persona, answers)
                bed_scores.append(match_pct)

        if not bed_scores:
            continue
        overall_pct = round(sum(bed_scores) / len(bed_scores), 2)

        # Min price formatting
        min_price = None
        if monthly_rents:
            min_price = f"{min(monthly_rents):.2f} {currency_symbol} / month"
        if daily_rents:
            d = f"{min(daily_rents):.2f} {currency_symbol} / day"
            min_price = f"{min_price}, {d}" if min_price else d

        # 7. Compute weighted sort score for all questions
        score = 0.0

        # Helper to iterate multi-select entries
        def weighted_block(q_key, func):
            nonlocal score
            for entry in prefs.get(q_key, []):
                val = entry['value']
                prio = entry['priority']
                sub = func(val)
                score += sub * prio

        # Availability Start Date
        def avail_func(val):
            if not all_start_dates: return 0
            if "As Soon as Possible" in val: tgt=0
            elif "1 Month" in val: tgt=30
            elif "3 Months" in val: tgt=90
            else: tgt=float('inf')
            actual = min((d - today).days for d in all_start_dates)
            diff = abs(actual - tgt)
            return max(0, 1 - diff / tgt) if tgt and tgt!=float('inf') else 0
        weighted_block("Availability Start Date", avail_func)

        # Lease Duration Preference
        mapping = {"Short-term":6, "Medium-term":12, "Long-term":36, "Very Long-term":60}
        def lease_func(val):
            if not all_min_durations: return 0
            tgt = next((v for k,v in mapping.items() if k in val), None)
            if not tgt: return 0
            diff=abs(min(all_min_durations)-tgt)
            return max(0, 1 - diff/tgt)
        weighted_block("Lease Duration Preference", lease_func)

        # Pet Ownership Preference
        def pet_func(val):
            allows = "Pet-Friendly" in amenities
            if "No Pets" in val: return 0 if allows else 1
            return 1 if allows else 0
        weighted_block("Pet Ownership Preference", pet_func)

        # Alcohol Consumption Preference
        def alc_func(val):
            allows = "Alcohol Allowed" in amenities
            if "No Preference" in val: return 1
            return 1 if "Allowed" in val and allows else 0
        weighted_block("Alcohol Consumption Preference", alc_func)

        # Smoking Preference
        def smoke_func(val):
            allows = "Smoking Allowed" in amenities
            if "No Preference" in val: return 1
            return 1 if "Allowed" in val and allows else 0
        weighted_block("Smoking Preference", smoke_func)

        # Maximum Number of People Allowed
        def people_func(val):
            if max_people is None: return 0
            tgt=parse_numeric(val)
            diff=abs(tgt-max_people)
            return max(0, 1 - diff/max(tgt,max_people,1))
        weighted_block("Maximum Number of People Allowed", people_func)

        # Number of Beds Required
        def beds_func(val):
            want=parse_numeric(val); have=prop.number_of_rooms
            diff=abs(want-have)
            return max(0, 1 - diff/max(want,have,1))
        weighted_block("Number of Beds Required", beds_func)

        # Budget for Rent per Month
        def bud_func(val):
            if not monthly_rents: return 0
            low,high=parse_range(val)
            prop_min=min(monthly_rents)
            dist=max(0, low-prop_min, prop_min-high)
            span=high-low or high or 1
            return max(0, (span-dist)/span)
        weighted_block("Budget for Rent per Month", bud_func)

        # Preferred Amenities
        def am_func(val):
            want={x.strip() for x in val.split(',')}
            inter=len(want & set(amenities))
            union=len(want | set(amenities)) or 1
            return inter/union
        weighted_block("Preferred Amenities", am_func)

        # Preferred Room Location in Property
        def loc_func(val):
            return 1 if any(room.location_in_property.lower() in val.lower() for room in prop.rooms.all()) else 0
        weighted_block("Preferred Room Location in Property", loc_func)

        # Preferred Floor Level
        def floor_func(val):
            if prop.floor is None: return 0
            want=parse_numeric(val); diff=abs(want-prop.floor)
            return max(0, 1 - diff/max(want,prop.floor,1))
        weighted_block("Preferred Floor Level", floor_func)

        # Preferred Property Size
        def size_func(val):
            if not prop.property_size: return 0
            low,high=parse_range(val)
            act=parse_numeric(prop.property_size)
            if act is None: return 0
            dist=max(0, low-act, act-high)
            span=high-low or high or 1
            return max(0, (span-dist)/span)
        weighted_block("Preferred Property Size", size_func)

        # Number of Bathrooms
        def bath_func(val):
            want=parse_numeric(val)
            bath=parse_numeric(next((a for a in amenities if "Bathroom" in a), ""))
            if bath is None: return 0
            diff=abs(want-bath)
            return max(0, 1 - diff/max(want,bath,1))
        weighted_block("Number of Bathrooms", bath_func)

        # Number of Bedrooms
        def bedr_func(val):
            want=parse_numeric(val); have=prop.number_of_rooms
            diff=abs(want-have)
            return max(0, 1 - diff/max(want,have,1))
        weighted_block("Number of Bedrooms", bedr_func)

        # Preferred Property Type
        def type_func(val):
            return 1 if prop.property_type and val == prop.property_type.type_name else 0
        weighted_block("Preferred Property Type", type_func)

        # Distance
        dist_center = haversine_distance(
            float(prop.latitude or 0), float(prop.longitude or 0),
            float(city_obj.latitude), float(city_obj.longitude)
        )

        results.append({
            "id": prop.id,
            "property_name": prop.property_name,
            "distance_from_city_center": dist_center,
            "property_size": prop.property_size,
            "property_type": prop.property_type.type_name if prop.property_type else None,
            "property_city": prop.property_city.name if prop.property_city else None,
            "number_of_rooms": prop.number_of_rooms,
            "floor": prop.floor,
            "property_description": prop.property_description,
            "amenities": amenities,
            "media": media,
            "currency_symbol": currency_symbol,
            "currency": currency,
            "min_price": min_price,
            "overall_personality_match_percentage": overall_pct,
            "sort_score": score,
        })

    # 8. Sort and remove sort_score
    results.sort(key=lambda x: (x['sort_score'], x['overall_personality_match_percentage']), reverse=True)
    for r in results:
        r.pop('sort_score', None)

    return Response(
        ResponseData.success({
            "preferred_city_name": city_obj.name,
            "landlord_id": last_landlord,
            "properties": results
        }, "Properties fetched successfully"),
        status=200
    )

'''
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_properties_by_city_overview(request):
    """
    API to fetch high-level property summaries in a city:
     - overall_personality_match_percentage
     - min_price
     - media, amenities, distance, etc.
    (no per-bed details)
    """
    print(f'request.data {request.data}')
    serializer = PropertyListRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=400
        )

    city_id = serializer.validated_data['city_id']
    tenant_id = serializer.validated_data['tenant_id']
    # Load tenant & update preferred city
    try:
        cityData = CityModel.objects.get(id=city_id)
    except CityModel.DoesNotExist:
        return Response(
            ResponseData.success_without_data("City not found"),
            status=status.HTTP_200_OK
        )
    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True)
        tenant.preferred_city_id = city_id    # set the *_id field directly
        tenant.save(update_fields=['preferred_city'])
        print('svdsvsdvdssvdv')
        print(tenant.preferred_city)
    except TenantDetailsModel.DoesNotExist:
        return Response(
            ResponseData.error("Tenant not found"),
            status=404
        )

    # Load tenant personality
    try:
        tenant_persona = TenantPersonalityDetailsModel.objects.get(
            tenant=tenant, is_active=True, is_deleted=False
        )
    except TenantPersonalityDetailsModel.DoesNotExist:
        tenant_persona = None

    # Get currency symbol + city name
    city_obj = CityModel.objects.filter(id=city_id).select_related('state__country').first()
    print(f'city_obj {city_obj}')
    currency_symbol = (
        city_obj.state.country.currency_symbol
        if city_obj and city_obj.state and city_obj.state.country else ""
    )
    currency = (
        city_obj.state.country.currency
        if city_obj and city_obj.state and city_obj.state.country else ""
    )
    city_name = city_obj.name if city_obj else None

    # Prefetch beds only for scoring
    properties = (
        LandlordPropertyDetailsModel.objects
        .filter(property_city_id=city_id, is_active=True, is_deleted=False)
        .select_related('property_type', 'property_city')
        .prefetch_related(
            Prefetch(
                'rooms__beds',
                queryset=LandlordRoomWiseBedModel.objects.filter(
                    is_active=True,
                    is_deleted=False,
                    availability_start_date__isnull=False
                ).prefetch_related('tenant_preference_answers'),
                to_attr='valid_beds'
            )
        )
        .prefetch_related('property_media', 'amenities')
    )
    print(f'properties {properties}')
    # scoring setup
    personality_fields = [
        "occupation", "country", "religion", "income_range",
        "smoking_habit", "drinking_habit", "socializing_habit",
        "relationship_status", "food_habit", "pet_lover"
    ]
    max_marks = 10
    total_possible = len(personality_fields) * max_marks

    result = []
    landlord_id = None

    for prop in properties:
        landlord_id = prop.landlord_id

        # gather min_price across beds
        monthly = []
        daily = []

        # gather all media & amenities
        media = [
            {"url": m.file.url, "type": m.media_type}
            for m in prop.property_media.filter(is_active=True)
        ]
        amenities = [a.name for a in prop.amenities.filter(is_active=True)]

        # scoring: average across every available bed
        bed_matches = []
        print("\n=== STARTING BED MATCH CALCULATION ===")
        print(f"Total rooms in property: {prop.rooms.count()}")
        for room_idx, room in enumerate(prop.rooms.all(), start=1):
            print(f"\nProcessing room {room_idx} (ID: {room.id})")
            valid_beds = getattr(room, 'valid_beds', [])
            print(f"Found {len(valid_beds)} beds in this room")
            
            for bed_idx, bed in enumerate(valid_beds, start=1):
                print(f"\n- Bed {bed_idx} (ID: {bed.id}, Rent: {bed.rent_amount}, Monthly: {bed.is_rent_monthly})")
                
                # Price buckets
                (monthly if bed.is_rent_monthly else daily).append(bed.rent_amount)
                print(f"Added to {'monthly' if bed.is_rent_monthly else 'daily'} price bucket")

                # Landlord answers
                lan = list(bed.tenant_preference_answers.all())
                print(f"Found {len(lan)} preference answers directly on bed")
                
                if not lan:
                    print("No bed-specific answers, checking base preferences...")
                    base = LandlordBasePreferenceModel.objects.filter(
                        landlord_id=landlord_id
                    ).first()
                    if base:
                        lan = list(base.answers.all())
                        print(f"Found {len(lan)} base preference answers")
                    else:
                        print("No base preferences found either")

                overall_match, breakdown = compute_personality_match(tenant_persona, lan)
                print("Overall match:", overall_match)
                for field, pct in breakdown.items():
                    print(f" • {field}: {pct}%")
                bed_matches.append(overall_match)
                print(f"Added to bed_matches (now has {len(bed_matches)} items)")

        print("\n=== FINISHED BED MATCH CALCULATION ===")
        print(f"Total beds processed: {len(bed_matches)}")
        print(f"bed_matches contents: {bed_matches}")
        print(f'bed_matchesscs {bed_matches}')
        if bed_matches:
            # overall & min_price
            overall = round(sum(bed_matches) / len(bed_matches), 2)
            min_price = None
            if monthly:
                min_price = f"{min(monthly):.2f} {currency_symbol} / month"
            if daily:
                d = f"{min(daily):.2f} {currency_symbol} / day"
                min_price = f"{min_price}, {d}" if min_price else d
        else:
            continue
        print(f'prop.latitude {prop.latitude}')
        print(f'prop.longitude {prop.longitude}')
        print(f'city_obj.latitude {city_obj.latitude}')
        print(f'city_obj.latitude {city_obj.longitude}')
        result.append({
            "id": prop.id,
            "property_name": prop.property_name,
            "distance_from_city_center": haversine_distance(
                float(prop.latitude), float(prop.longitude),
                float(city_obj.latitude), float(city_obj.longitude)
            ),
            "property_size": prop.property_size,
            "property_type": prop.property_type.type_name if prop.property_type else None,
            "property_city": prop.property_city.name if prop.property_city else None,
            "number_of_rooms": prop.number_of_rooms,
            "floor": prop.floor,
            "property_description": prop.property_description,
            "amenities": amenities,
            "media": media,
            "currency_symbol" : currency_symbol,
            "currency" : currency,
            "min_price": min_price,
            "overall_personality_match_percentage": overall_match,
            
        })

    return Response(
        ResponseData.success({
            "preferred_city_name": city_name,
            "landlord_id": landlord_id,
            "properties": result
        }, "Properties fetched successfully"),
        status=200
    )
'''



@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_property_details(request):
    """
    API to fetch detailed property info (rooms & beds), including:
      - is_phone_verified, is_payment_active (tenant)
      - per-bed personality_match_percentage
    """
    serializer = PropertyDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error("Validation error", serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    property_id = serializer.validated_data['property_id']
    tenant_id = serializer.validated_data['tenant_id']

    # fetch prop
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
                    is_active=True, is_deleted=False
                ).prefetch_related(
                    'room_media',
                    Prefetch(
                        'beds',
                        queryset=LandlordRoomWiseBedModel.objects.filter(
                            is_active=True, is_deleted=False
                        ).prefetch_related(
                            'bed_media',
                            'tenant_preference_answers'
                        )
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

    # tenant phone/payment
    tenant = TenantDetailsModel.objects.filter(id=tenant_id).first()
    is_phone_verified = bool(tenant and tenant.phone_number)
    is_payment_active = False
    if tenant:
        pay = TenantPaymentModel.objects.filter(
            tenant=tenant, is_active=True, is_deleted=False
        ).order_by('-paid_at').first()
        if pay and pay.paid_at + timedelta(days=30) > now():
            is_payment_active = True

    # load tenant persona once
    try:
        tenant_persona = TenantPersonalityDetailsModel.objects.get(
            tenant_id=tenant_id, is_active=True, is_deleted=False
        )
    except TenantPersonalityDetailsModel.DoesNotExist:
        tenant_persona = None

    # scoring setup
    pfields = [
        "occupation", "country", "religion", "income_range",
        "smoking_habit", "drinking_habit", "socializing_habit",
        "relationship_status", "food_habit", "pet_lover"
    ]
    max_marks = 10
    tot = len(pfields) * max_marks

    # build response
    property_media = [
        {"url": m.file.url, "type": m.media_type}
        for m in prop.property_media.filter(is_active=True)
    ]
    amenities = [a.name for a in prop.amenities.filter(is_active=True)]

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
            # score this bed
            lan = list(bed.tenant_preference_answers.all())
            if not lan:
                base = LandlordBasePreferenceModel.objects.filter(
                    landlord_id=prop.landlord_id
                ).first()
                if base:
                    lan = list(base.answers.all())

            overall_match, breakdown = compute_personality_match(tenant_persona, lan)
            print("Overall match:", overall_match)
            for field, pct in breakdown.items():
                print(f" • {field}: {pct}%")
            beds_data.append({
                "bed_id": bed.id,
                "bed_number": bed.bed_number,
                "is_available": bed.is_available,
                "is_rent_monthly": bed.is_rent_monthly,
                "min_agreement_duration_in_months": bed.min_agreement_duration_in_months,
                "rent_amount": str(bed.rent_amount),
                "availability_start_date": bed.availability_start_date.strftime("%d %b %y")
                    if bed.availability_start_date else "",
                "availability_end_date": bed.availability_end_date.strftime("%d %b %y")
                    if getattr(bed, 'availability_end_date', None) else "",
                "bed_media": bed_media,
                "personality_match_percentage": overall_match,
                "is_phone_verified": is_phone_verified,
                "is_payment_active": is_payment_active,
                'details_of_personality_match' : breakdown
            })

        rooms_data.append({
            "room_id": room.id,
            "room_type": room.room_type.type_name if room.room_type else None,
            "room_size": room.room_size,
            "number_of_beds": room.number_of_beds or 1,
            "max_people_allowed": room.max_people_allowed or 1,
            "current_male_occupants": room.current_male_occupants or 0,
            "current_female_occupants": room.current_female_occupants or 0,
            "floor": room.floor or 0,
            "location_in_property": room.location_in_property,
            "room_media": room_media,
            "beds": beds_data
        })

    return Response(
        ResponseData.success(rooms_data, "Property details fetched successfully"),
        status=status.HTTP_200_OK
    )