from decimal import ROUND_HALF_UP, Decimal
import json
import os
import re
import shutil
from typing import Any, Dict, List
from rest_framework.decorators import api_view,parser_classes
from rest_framework.response import Response
from rest_framework import status
from localization.models import CityModel, CountryModel
from notifications.models import TenantDeviceNotificationModel
from notifications.send_notifications import send_onesignal_notification
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from response import Response as ResponseData
from tenant.views import send_otp_email
from translation_utils import DEFAULT_LANGUAGE_CODE, get_translation
from translations.models import LanguageModel
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from tenant.models import TenantDetailsModel
from user.fetch_match_details import compute_personality_match
from user.jwt_utils import get_tokens_for_user
from .models import LandlordBasePreferenceModel, LandlordBedMediaModel, LandlordDetailsModel, LandlordDocumentTypeModel, LandlordEmailVerificationModel, LandlordIdentityVerificationFile, LandlordIdentityVerificationModel, LandlordOptionModel, LandlordPropertyAmenityModel, LandlordPropertyDetailsModel, LandlordPropertyMediaModel, LandlordPropertyRoomDetailsModel, LandlordPropertyRoomTypeModel, LandlordPropertyTypeModel, LandlordQuestionModel, LandlordRoomMediaModel
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils.timezone import now
import random
from django.core.files import File
from django.db.models import Prefetch
from django.contrib.contenttypes.models import ContentType
from .models import LandlordQuestionModel, LandlordAnswerModel, LandlordRoomWiseBedModel
from .serializers import AddIdentityDocumentSerializer, CheckPropertyExistsSerializer, LandlordBasePreferenceSerializer, LandlordBedDetailRequestSerializer, LandlordDocumentTypeSerializer, LandlordIdentityDocumentSerializer, LandlordPreferenceAnswerSerializer, LandlordProfileRequestSerializer, LandlordPropertyDetailRequestSerializer, LandlordPropertyDetailSerializer, LandlordQuestionRequestSerializer, LandlordRoomDetailRequestSerializer, LandlordSignupSerializer, PropertyAllPreferencesRequestSerializer, PropertyListRequestSerializer, TenantInterestRequestSerializer, ToggleActiveStatusSerializer, UpdateLandlordProfileSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

PENDING_OR_ACCEPTED = ["pending", "accepted"]
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def landlord_signup(request):
    """API to handle landlord signup"""
    try:
        print(request.data)
        serializer = LandlordSignupSerializer(data=request.data)
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

            # Try to get language for the tenant from the request if provided
            preferred_language = None
            try:
                preferred_language = LanguageModel.objects.get(code=language_code)
            except LanguageModel.DoesNotExist:
                preferred_language = None

            # If the tenant exists but is not active
            if landlord is not None and landlord.is_active is False:
                # Check for existing, unverified OTP
                landlord_verification = LandlordEmailVerificationModel.objects.filter(
                    landlord=landlord,
                    is_verified=False
                ).first()
                otp = str(random.randint(100000, 999999))  # Generate OTP
                if landlord_verification:
                    # Generate a new OTP and send email
                    landlord_verification.otp = otp
                    landlord_verification.created_at = now()
                    landlord_verification.save()
                    send_otp_email(landlord.email, otp)
                else:
                    # No unverified OTP exists; create a new verification entry
                    LandlordEmailVerificationModel.objects.create(
                        landlord=landlord,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(landlord.email, otp)
                message = get_translation("SUCC_LANDLORD_OTP_SENT", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )
            elif landlord is not None and landlord.is_active is True:
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
                    landlord = LandlordDetailsModel.objects.create(**validated_data)
                    # Generate OTP for the new tenant
                    otp = str(random.randint(100000, 999999))
                    LandlordEmailVerificationModel.objects.create(
                        landlord=landlord,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(landlord.email, otp)
                    message = get_translation("SUCC_LANDLORD_SIGNUP_VERIFY", language_code)
                    tokens = get_tokens_for_user(landlord)
                
                    return Response(
                        ResponseData.success(data={
                            'tokens' : tokens,
                            'id' : landlord.id
                        }, message=message),
                        status=status.HTTP_201_CREATED
                    )
                else:
                    # If no password is provided, create tenant as active directly.
                    if preferred_language:
                        validated_data['preferred_language'] = preferred_language
                    landlord = LandlordDetailsModel.objects.create(**validated_data, is_active=True)
                    message = get_translation("SUCC_LANDLORD_SIGNUP", language_code)
                    tokens = get_tokens_for_user(landlord)
                    return Response(
                        ResponseData.success(data={
                            'tokens' : tokens,
                            'id' : landlord.id
                        }, message=message),
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
def get_preference_questions(request):
    """
    ...existing docstring...
    """
    serializer = LandlordQuestionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    landlord_id    = serializer.validated_data["user_id"]
    bed_id         = serializer.validated_data.get("bed_id")
    use_base       = serializer.validated_data.get("is_base_preference", False)
    client_answers = serializer.validated_data.get("answers", [])

    # 1) fetch landlord
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord"),
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) client_map unchanged
    client_map = {
        ans["question_id"]: ans
        for ans in client_answers
        if "question_id" in ans
    }

    # 3) build bed_map unchanged
    bed_map: Dict[int, List[Dict[str,int]]] = {}
    if bed_id is not None:
        bed_qs = LandlordRoomWiseBedModel.objects.filter(id=bed_id).first()
        if bed_qs:
            for a in bed_qs.tenant_preference_answers.filter(is_active=True, is_deleted=False):
                bed_map.setdefault(a.question_id, []).append({
                    "option_id": a.object_id,
                    "preference": a.preference
                })

    # 4) build base_map only if use_base (unchanged)
    base_map: Dict[int, List[Dict[str,int]]] = {}
    if use_base:
        base = LandlordBasePreferenceModel.objects.filter(landlord=landlord).first()
        if base:
            for a in base.answers.filter(is_active=True, is_deleted=False):
                base_map.setdefault(a.question_id, []).append({
                    "option_id": a.object_id,
                    "preference": a.preference
                })

    # --- NEW: load _all_ base answers for the flag, regardless of use_base ---
    base_all = []
    base_pref_all = LandlordBasePreferenceModel.objects.filter(landlord=landlord).first()
    if base_pref_all:
        base_all = list(base_pref_all.answers.filter(is_active=True, is_deleted=False))

    # 5) compute flag from bed_map OR base_all
    is_preference_found = bool(bed_map) or bool(base_all)

    # 6) fetch questions + build response exactly as before...
    questions = LandlordQuestionModel.objects.filter(
        is_active=True, is_deleted=False
    ).select_related("question_type", "content_type")

    response: List[Dict[str,Any]] = []
    for q in questions:
        qd = {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": {
                "id":   q.question_type.id,
                "type_name": q.question_type.type_name,
                "description": q.question_type.description,
            },
            "question_options": [],
            "answers": []
        }

        # build options (unchanged)…
        if q.content_type:
            model = q.content_type.model_class()
            if model is not None:
                opts = [
                  {"id": o.id, "option_text": getattr(o, "title", str(o))}
                  for o in model.objects.filter(is_active=True, is_deleted=False)
                ]
                qd["question_options"] = opts

        # select answers exactly as before (client_map → bed_map → base_map)
        if q.id in client_map:
            payload = client_map[q.id]
            for idx, opt_id in enumerate(payload.get("priority_order", []), start=1):
                qd["answers"].append({"option_id": opt_id, "preference": idx})

        elif q.id in bed_map:
            for entry in sorted(bed_map[q.id], key=lambda x: x["preference"]):
                qd["answers"].append(entry)

        elif q.id in base_map:
            for entry in sorted(base_map[q.id], key=lambda x: x["preference"]):
                qd["answers"].append(entry)

        response.append(qd)

    # 7) return with the new flag included
    return Response(
        ResponseData.success(
            {
              "questions": response,
              "isPreferenceFound": is_preference_found
            },
            "Preferences fetched"
        ),
        status=status.HTTP_200_OK
    )




@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def save_landlord_preferences(request):
    """
    Save or update a landlord’s tenant-preference answers for a specific bed.
    Expects payload:
      {
        "user_id": <landlord_id>,
        "bed_id": <bed_record_id>,
        "answers": [
          { "question_id": 45, "priority_order": [3,7,2] },
          ...
        ]
      }
    """
    print(f'requestccsc {request.data}')
    serializer = LandlordPreferenceAnswerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    landlord_id = data["user_id"]
    bed_id      = data["bed_id"]
    answers     = data.get("answers", [])

    # 1) validate landlord
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) validate bed record
    bed_record = LandlordRoomWiseBedModel.objects.filter(
        id=bed_id,
        room__property__landlord=landlord,
        is_active=True,
        is_deleted=False
    ).first()
    if not bed_record:
        return Response(
            ResponseData.error("Invalid bed_id or bed does not belong to this landlord."),
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3) upsert answers & collect their IDs
    answer_instances = []
    for ans in answers:
        q_id = ans.get("question_id")
        selected_answers = ans.get("priority_order", [])

        # validate question
        question = LandlordQuestionModel.objects.filter(
            id=q_id, is_active=True, is_deleted=False
        ).first()
        if not question:
            return Response(
                ResponseData.error(f"Invalid question_id: {q_id}"),
                status=status.HTTP_400_BAD_REQUEST
            )

        # get the right content-type for this question's options
        ct = question.content_type
        if not ct:
            return Response(
                ResponseData.error(f"Question {q_id} has no content_type defined."),
                status=status.HTTP_400_BAD_REQUEST
            )

        # for each selected option, create or update the answer record
        for priority, option_id in enumerate(selected_answers, start=1):  # Index represents priority
                print(f'priority,option_id {priority} , {option_id}')
                option_content_type = ContentType.objects.get_for_model(question.content_type.model_class())
                option_obj = option_content_type.get_object_for_this_type(id=option_id)
                if not option_obj:
                    return Response(
                        {"status": "error", "message": f"Invalid option ID: {option_id} for question ID: {q_id}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                answer_instance, created = LandlordAnswerModel.objects.update_or_create(
                    landlord=landlord,
                    question=question,
                    preference=priority,
                    content_type=option_content_type,
                    object_id=option_id,
                )
                print(f'answer_instance123 {answer_instance}')
                answer_instances.append(answer_instance.id)
    # 4) replace the M2M set on that bed record
    bed_record.tenant_preference_answers.set(answer_instances)
    # 5) build and save the human-readable "Room X Bed Y" label
    #    get all rooms for this property in a stable order (e.g. by PK)
    rooms_qs = LandlordPropertyRoomDetailsModel.objects.filter(
        property=bed_record.room.property
    ).order_by("id")
    rooms = list(rooms_qs)
    try:
        room_index = rooms.index(bed_record.room)
    except ValueError:
        room_index = 0

    bed_number = bed_record.bed_number  # fallback if somehow null
    bed_record.tenant_preference = f"Room {room_index+1} Bed {bed_number} Preference"
    print(f'bed_record.tenant_preference {bed_record.tenant_preference}')
    bed_record.save(update_fields=["tenant_preference"])
    
    return Response(
        ResponseData.success_without_data("Tenant preferences saved for bed successfully."),
        status=status.HTTP_200_OK
    )


def parse_room_and_bed(tenant_preference_same_as):
    # Regular expression to capture integers after "Room" and "Bed"
    pattern = r"Room (\d+) Bed (\d+)"
    match = re.match(pattern, tenant_preference_same_as)

    if match:
        room_number = int(match.group(1))  # Extract the room number
        bed_number = int(match.group(2))  # Extract the bed number
        return room_number, bed_number
    else:
        raise ValueError("Invalid format for tenant_preference_same_as")

def get_media_type(file_name):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv']
    lower_file_name = file_name.lower()
    for ext in image_extensions:
        if lower_file_name.endswith(ext):
            return "image"
    for ext in video_extensions:
        if lower_file_name.endswith(ext):
            return "video"
    # Default to image if unknown (or you could return None)
    return "image"

def save_landlord_answers(bd,landlord,answer_instances):
    answers = bd.get("bed_preferences", [])
    print('456')
    for answer in answers:
        # question_id in answer
        question_id = answer.get("question_id")
        selected_answers = answer.get("priority_order", [])

        # Validate question
        question = LandlordQuestionModel.objects.filter(id=question_id, is_active=True).first()
        if not question:
            return Response(
                {"status": "error", "message": f"Invalid question ID: {question_id}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Depending on how you store question options, you'll also need to validate them.
        for priority, option_id in enumerate(selected_answers, start=1):  # Index represents priority
                print(f'priority,option_id {priority} , {option_id}')
                option_content_type = ContentType.objects.get_for_model(question.content_type.model_class())
                option_obj = option_content_type.get_object_for_this_type(id=option_id)
                if not option_obj:
                    return Response(
                        {"status": "error", "message": f"Invalid option ID: {option_id} for question ID: {question_id}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                answer_instance, created = LandlordAnswerModel.objects.update_or_create(
                    landlord=landlord,
                    question=question,
                    preference=priority,
                    content_type=option_content_type,
                    object_id=option_id,
                )
                print(f'answer_instance123 {answer_instance}')
                answer_instances.append(answer_instance.id)
    return answer_instances
    

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def add_landlord_property_details(request):
    # 1) Validate fields
    for key, value in request.POST.items():
        print(f"{key}: {value}")
    print(f'propertyCityddd {request.POST.get("propertyCity")}')
    landlord_id = request.POST.get("landlord_id")
    property_name = request.POST.get("propertyName")
    property_address = request.POST.get("propertyAddress")
    property_city = request.POST.get("propertyCity")
    pin_code = request.POST.get("pinCode")
    property_size = request.POST.get("propertySize")
    property_type_name = request.POST.get("propertyType")
    number_of_rooms = request.POST.get("number_of_rooms")
    floor = request.POST.get("floor")
    property_description = request.POST.get("propertyDescription", "")
    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")
    streetNumber = request.POST.get('streetNumber')
    amenities_json = request.POST.get("amenities")
    rooms_json = request.POST.get("rooms")
    rooms_data = json.loads(rooms_json)
    print(f'rooms_data {rooms_data}')
    if not all([landlord_id, property_name, property_address, property_size, property_type_name, number_of_rooms]):
        return Response({"status": "error", "message": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    # 2) Validate landlord
    try:
        landlord = LandlordDetailsModel.objects.get(id=landlord_id, is_deleted=False, is_active=True)
    except LandlordDetailsModel.DoesNotExist:
        return Response({"status": "error", "message": "Invalid landlord or inactive/deleted."}, status=status.HTTP_400_BAD_REQUEST)

    # 3) Validate property type
    try:
        prop_type = LandlordPropertyTypeModel.objects.get(type_name=property_type_name, is_active=True, is_deleted=False)
    except LandlordPropertyTypeModel.DoesNotExist:
        return Response({"status": "error", "message": "Invalid propertyType ID."}, status=status.HTTP_400_BAD_REQUEST)

    property_city_instance = (
        CityModel.objects
        .filter(name=property_city)
        .first()
    )
    # 4) Create property
    property_instance = LandlordPropertyDetailsModel.objects.create(
        landlord=landlord,
        property_name=property_name,
        property_address=property_address,
        property_city=property_city_instance,
        pin_code=pin_code,
        property_size=property_size,
        property_type=prop_type,
        number_of_rooms=number_of_rooms,
        floor=floor if floor else None,
        property_description=property_description,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        street_number=streetNumber
    )

    # 5) Multiple property images/videos
    # property_images[] is a list of image files
    # property_videos[] is a list of video files
    base_dir = os.path.join(settings.MEDIA_ROOT, 'temp_landlord_data', f"landlord_{landlord_id}")
    print(f'base_dir123 {base_dir}')
    property_dir = os.path.join(base_dir, 'property')
    if not os.path.exists(property_dir):
        print(f"Property directory {property_dir} does not exist. Skipping.")
    else:
        for file_name in os.listdir(property_dir):
            print(f'file_name {file_name}')
            file_path = os.path.join(property_dir, file_name)
            # Check if it's a file (skip directories)
            if os.path.isfile(file_path):
                try:
                    # Determine media type
                    media_type = get_media_type(file_name)
                    with open(file_path, 'rb') as f:
                        django_file = File(f, name=file_name)
                        LandlordPropertyMediaModel.objects.create(
                            property=property_instance,  # Ensure property_instance is defined
                            file=django_file,
                            media_type=media_type,
                        )
                    print(f"Created media object for: {file_path} as {media_type}")
                except Exception as e:
                    print(f"Error creating media object for {file_path}: {str(e)}")

    # 6) Amenities
    if amenities_json:
        try:
            amenities_list = json.loads(amenities_json)
        except:
            amenities_list = []
        print(f'amenities_list {amenities_list}')
        if amenities_list:
            valid_amenities = LandlordPropertyAmenityModel.objects.filter(
                id__in=amenities_list,
                is_active=True,
                is_deleted=False
            )
            if len(valid_amenities) != len(amenities_list):
                return Response({"status": "error", "message": "One or more amenity IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)
            property_instance.amenities.set(valid_amenities)
    # 7) Rooms
    if rooms_json:
        print(f'rooms_json {rooms_json}')
        rooms_data = json.loads(rooms_json)
        print(f'rooms_data {rooms_data}')
        for idx, rm in enumerate(rooms_data):
            room_type_id = rm.get("room_type")
            room_size = rm.get("room_size")
            room_name = rm.get("room_name")
            loc = rm.get("location_in_property", "")
            n_beds = rm.get("number_of_beds")
            r_floor = rm.get("floor")
            n_windows = rm.get("number_of_windows")
            max_people_allowed = rm.get("max_people_allowed")
            current_male_occupants = rm.get("current_male_occupants")
            current_female_occupants = rm.get("current_female_occupants")

            if not room_type_id or not room_size:
                continue

            try:
                room_type_obj = LandlordPropertyRoomTypeModel.objects.get(id=room_type_id, is_active=True, is_deleted=False)
            except LandlordPropertyRoomTypeModel.DoesNotExist:
                continue

            room_instance = LandlordPropertyRoomDetailsModel.objects.create(
                property=property_instance,
                room_type=room_type_obj,
                room_name=room_name,
                room_size=room_size,
                number_of_beds=n_beds if n_beds else None,
                number_of_windows=n_windows if n_windows else None,
                max_people_allowed=max_people_allowed if max_people_allowed else None,
                current_male_occupants=current_male_occupants if current_male_occupants else None,
                current_female_occupants=current_female_occupants if current_female_occupants else None,
                floor=r_floor if r_floor else None,
                location_in_property=loc
            )
            print(f'base_dir123 {base_dir}')
            room_dir = os.path.join(base_dir, f'room_{idx}')
            if not os.path.exists(room_dir):
                print(f"Room directory {room_dir} does not exist. Skipping.")
            else:
                for file_name in os.listdir(room_dir):
                    print(f'file_name {file_name}')
                    file_path = os.path.join(room_dir, file_name)
                    # Check if it's a file (skip directories)
                    if os.path.isfile(file_path):
                        try:
                            # Determine media type
                            media_type = get_media_type(file_name)
                            with open(file_path, 'rb') as f:
                                django_file = File(f, name=file_name)
                                LandlordRoomMediaModel.objects.create(
                                    room=room_instance,  # Ensure property_instance is defined
                                    file=django_file,
                                    media_type=media_type,
                                )
                            print(f"Created media object for: {file_path} as {media_type}")
                        except Exception as e:
                            print(f"Error creating media object for {file_path}: {str(e)}")

            # 7.2) Beds
            beds_data = rm.get("beds", [])
            any_available_bed = False
            print(f'beds_data12345 {beds_data}')
            for b_idx, bd in enumerate(beds_data):
                bed_number = bd.get("bed_number")
                is_rent_monthly = bd.get("is_rent_monthly")
                min_agreement_duration_in_months = bd.get("min_agreement_duration_in_months")
                rent_amount = bd.get("rent_amount")
                availability_start_date = bd.get("availability_start_date")
                is_available = False if availability_start_date is None else True
                print('123')
                if availability_start_date is not None:
                    any_available_bed = True
                if not rent_amount:
                    continue
                # 7.4) Bed preferences (if any)
                answer_instances = []
                answer_instances = save_landlord_answers(bd,landlord,answer_instances)
                print(f'answer_instances {answer_instances}')
                # 7.4) Bed preferences (if any)
                # Could be part of bd["bed_preferences"]
                # Omitted if not needed; else handle logic similarly.

                # Create the bed_instance with conditional values
                bed_instance = LandlordRoomWiseBedModel.objects.create(
                    room=room_instance,
                    bed_number=bed_number,
                    is_active= False if availability_start_date is None else True,
                    is_available=is_available,
                    rent_amount=rent_amount,
                    availability_start_date=None if availability_start_date == "" else availability_start_date,
                    is_rent_monthly=is_rent_monthly,
                    min_agreement_duration_in_months= 0 if not is_rent_monthly else min_agreement_duration_in_months,
                    tenant_preference= "" if bd.get("tenant_preference") is None else '',
                )


                bed_instance.tenant_preference_answers.set(answer_instances)  # Use .set() AFTER creation
                if answer_instances:
                    # room_idx is your index of this room in whatever list you're iterating;
                    # bed_number is the 1-based number you passed in.
                    pref_str = f"Room {idx+1} Bed {bed_number} Preference"
                    bed_instance.tenant_preference = pref_str
                    bed_instance.save()
                print(f'Answer Instances: {answer_instances}')
                for answer in bed_instance.tenant_preference_answers.all():
                    print(f'Answer ID: {answer.id}, Question: {answer.question.question_text}, Selected Option: {answer.object_id}')
                # 7.3) Bed media
                # Expecting form fields like room_0_bed_0_images[], room_0_bed_0_videos[], etc.
                print(f'base_dir123 {base_dir}')
                bed_dir = os.path.join(base_dir, f'room_{idx}',f'bed_{b_idx}')
                if not os.path.exists(bed_dir):
                    print(f"Bed directory {bed_dir} does not exist. Skipping.")
                else:
                    for file_name in os.listdir(bed_dir):
                        print(f'file_name {file_name}')
                        file_path = os.path.join(bed_dir, file_name)
                        # Check if it's a file (skip directories)
                        if os.path.isfile(file_path):
                            try:
                                # Determine media type
                                media_type = get_media_type(file_name)
                                with open(file_path, 'rb') as f:
                                    django_file = File(f, name=file_name)
                                    LandlordBedMediaModel.objects.create(
                                        bed=bed_instance,  # Ensure property_instance is defined
                                        file=django_file,
                                        media_type=media_type,
                                    )
                                print(f"Created media object for: {file_path} as {media_type}")
                            except Exception as e:
                                print(f"Error creating media object for {file_path}: {str(e)}")
            if any_available_bed == False:
                room_instance.is_active = False
                room_instance.save()
        if os.path.exists(base_dir):
            try:
                shutil.rmtree(base_dir)
                print(f"Deleted directory: {base_dir}")
            except Exception as e:
                print(f"Error deleting directory {base_dir}: {e}")
        else:
            print(f"Directory does not exist: {base_dir}")
    # Assuming you have the property_city_instance
    tenant_ids = list(
        TenantDetailsModel.objects
        .filter(
            preferred_city=property_city_instance,
            is_active=True,
            is_deleted=False
        )
        .values_list('id', flat=True)
    )
    print(f'tenant_ids ${tenant_ids}')

    if tenant_ids:
        send_onesignal_notification(
        tenant_ids=tenant_ids,
        headings={"en": "New Property in Your Preferred City"},
        contents={"en": f"A landlord just listed “{property_name}” in {property_city}."},
        data={"property_id": property_instance.id, "type": "tenant_new_property"},
        )
    return Response({"status": "success", "message": "Property details saved successfully."}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_landlord_property_details(request):
    try:
        print(f'request33 {request}')
        # 1) log all incoming fields & files
        for k, v in request.POST.items():
            print(f"{k}: {v}")
        for k, f in request.FILES.items():
            print(f"File - {k}: {f.name}")

        # 2) validate & fetch property
        property_id = request.POST.get("property_id")
        if not property_id:
            return Response({"status":"error","message":"Missing property_id."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            prop = LandlordPropertyDetailsModel.objects.get(id=property_id, is_deleted=False)
        except LandlordPropertyDetailsModel.DoesNotExist:
            return Response({"status":"error","message":"Property not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # 3) update basic fields
        update_fields = {}
        def _set_if_changed(post_key, model_attr, clean=lambda x: x):
            if post_key in request.POST:
                val = clean(request.POST[post_key])
                if getattr(prop, model_attr) != val:
                    update_fields[model_attr] = val

        _set_if_changed("propertyName",      "property_name",      str.strip)
        _set_if_changed("propertySize",      "property_size",      str.strip)
        _set_if_changed("propertyDescription","property_description", lambda x: x.strip())
        _set_if_changed("floor",             "floor")
        _set_if_changed("number_of_rooms",   "number_of_rooms")

        if update_fields:
            LandlordPropertyDetailsModel.objects.filter(id=property_id).update(**update_fields)

        # 4) update amenities
        if "amenities" in request.POST:
            try:
                amen_list = json.loads(request.POST["amenities"])
            except:
                return Response({"status":"error","message":"Invalid amenities JSON."},
                                status=status.HTTP_400_BAD_REQUEST)

            valid = list(LandlordPropertyAmenityModel.objects.
                         filter(id__in=amen_list, is_active=True, is_deleted=False))
            if len(valid) != len(amen_list):
                return Response({"status":"error","message":"One or more amenity IDs are invalid."},
                                status=status.HTTP_400_BAD_REQUEST)
            prop.amenities.set(valid)
        # Assuming you have the property_city_instance
        tenants_for_property = (
            TenantDetailsModel.objects
            .filter(
                Q(
                    tenant_interest_requests__bed__room__property_id=property_id,
                    tenant_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    tenant_interest_requests__is_active=True,
                    tenant_interest_requests__is_deleted=False,
                )
                |
                Q(
                    landlord_interest_requests__bed__room__property_id=property_id,
                    landlord_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    landlord_interest_requests__is_active=True,
                    landlord_interest_requests__is_deleted=False,
                )
            )
            .distinct()
        )

        if tenants_for_property:
            send_onesignal_notification(
            tenant_ids=tenants_for_property,
            headings={"en": "Property details updated by landlord"},
            contents={"en": f"A landlord just updated “{prop.property_name}” in {prop.property_city}."},
            data={"property_id": prop.id, "type": "tenant_update_property"},
            )
        return Response({"status":"success","message":"Property details updated successfully."},
                        status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Unexpected error: {e}")
        return Response({"status":"error","message":str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_landlord_room(request):
    """
    Request: one room object in form-data under "room" as JSON, plus property_id.
     • room.id = -1 → create; otherwise update that room
     • property_id must always be present
     • Accepts an "available_from" key (ISO date string). If room_type is Private,
       sets that on the bed's availability_start_date.
    """
    try:
        # 1) validate property
        prop_id = request.POST.get("property_id")
        if not prop_id:
            return Response({"status": "error", "message": "Missing property_id."}, status=400)
        prop = LandlordPropertyDetailsModel.objects.filter(
            id=prop_id, is_deleted=False
        ).first()
        if not prop:
            return Response({"status": "error", "message": "Property not found."}, status=404)

        # 2) parse JSON payload
        try:
            room_data = json.loads(request.POST.get("room", "{}"))
            print(f'room_data {room_data}')
        except ValueError:
            return Response({"status": "error", "message": "Invalid room JSON."}, status=400)

        room_id = room_data.get("id", -1)
        beds = room_data.get('beds', [])
        if not beds:
            print(f'beds {beds}')
            # no beds → nothing to update
            availability = None
            rent_amount = None
            tenant_preference = None
        else:
            # 3) grab the first bed’s availability_start_date
            availability = beds[0].get('availability_start_date')
            rent_amount = beds[0].get('rent_amount')
            tenant_preference = beds[0].get('bed_tenant_preference')
        # 3) validate room_type
        rt = LandlordPropertyRoomTypeModel.objects.filter(
            id=room_data.get("room_type"), is_active=True, is_deleted=False
        ).first()
        if not rt:
            return Response({"status": "error", "message": "Invalid room_type."}, status=400)

        # 4) extract optional available_from
        room_data = json.loads(request.POST.get("room", "{}"))
        # will be string like "2025-04-23"
        print(f'availability {availability}')
        # 5) update vs create
        if room_id != -1:
            # update existing
            obj = LandlordPropertyRoomDetailsModel.objects.filter(id=room_id).first()
            if not obj:
                return Response({"status": "error", "message": "Room not found."}, status=404)

            updates = {}
            # standard fields
            for key, fld in [
                ("room_size", "room_size"),
                ("room_name", "room_name"),
                ("number_of_beds", "number_of_beds"),
                ("number_of_windows", "number_of_windows"),
                ("max_people_allowed", "max_people_allowed"),
                ("current_male_occupants", "current_male_occupants"),
                ("current_female_occupants", "current_female_occupants"),
                ("floor", "floor"),
                ("location_in_property", "location_in_property"),
            ]:
                if key in room_data and getattr(obj, fld) != room_data[key]:
                    updates[fld] = room_data[key]

            # room_type change?
            if obj.room_type_id != rt.id:
                updates["room_type"] = rt

            # apply updates to room
            if updates:
                LandlordPropertyRoomDetailsModel.objects.filter(id=room_id).update(**updates)

            # if private, update its single bed's availability
            if rt.type_name.lower() == "private" and availability:
                # assume exactly one bed per private room
                LandlordRoomWiseBedModel.objects.filter(
                    room_id=room_id, is_deleted=False
                ).update(availability_start_date=availability,rent_amount=rent_amount,is_active=True,
                         min_agreement_duration_in_months=room_data.get("min_agreement_duration_in_months"))
            if rt.type_name.lower() == "private" and tenant_preference:
                # assume exactly one bed per private room
                print(f'entered_here {tenant_preference}')
                LandlordRoomWiseBedModel.objects.filter(
                    room_id=room_id, is_deleted=False
                ).update(tenant_preference=tenant_preference,rent_amount=rent_amount,
                         min_agreement_duration_in_months=room_data.get("min_agreement_duration_in_months"))

        else:
            # create new room
            new_room = LandlordPropertyRoomDetailsModel.objects.create(
                property=prop,
                room_type=rt,
                room_size=room_data.get("room_size"),
                room_name=room_data.get("room_name"),
                number_of_beds=room_data.get("number_of_beds"),
                number_of_windows=room_data.get("number_of_windows"),
                max_people_allowed=room_data.get("max_people_allowed"),
                current_male_occupants=room_data.get("current_female_occupants"),
                current_female_occupants=room_data.get("current_female_occupants"),
                floor=room_data.get("floor"),
                location_in_property=room_data.get("location_in_property", ""),
            )

            room_type = rt.type_name.lower()

            if room_type == "private":
                # only create the one bed if we have an availability date
                    bed_obj = LandlordRoomWiseBedModel.objects.create(
                        room=new_room,
                        bed_number=1,
                        rent_amount=rent_amount,
                        is_rent_monthly=room_data.get("is_rent_monthly", True),
                        min_agreement_duration_in_months=room_data.get(
                            "min_agreement_duration_in_months", 0
                        ),
                        tenant_preference=tenant_preference,
                        availability_start_date=availability if availability else None
                    )
                    answer_instances = []
                    answer_instances = save_landlord_answers(beds[0],prop.landlord,answer_instances)
                    print(f'answer_instances {answer_instances}')
                    if answer_instances:
                        bed_obj.tenant_preference_answers.set(answer_instances)
 

            elif room_type == "sharing":
                # for a sharing room, always create two beds by default
                for bed_num in (1, 2):
                    LandlordRoomWiseBedModel.objects.create(
                        room=new_room,
                        bed_number=bed_num,
                        tenant_preference=tenant_preference,
                        rent_amount=room_data.get("rent_amount", 0),
                        is_rent_monthly=room_data.get("is_rent_monthly", True),
                        min_agreement_duration_in_months=room_data.get(
                            "min_agreement_duration_in_months", 0
                        ),
                        # if you do want to set availability only when provided, otherwise leave null:
                        availability_start_date=availability if availability else None,
                    )
        # Assuming you have the property_city_instance
        tenants_for_room = (
            TenantDetailsModel.objects
            .filter(
                Q(
                    tenant_interest_requests__bed__room_id=room_id,
                    tenant_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    tenant_interest_requests__is_active=True,
                    tenant_interest_requests__is_deleted=False,
                )
                |
                Q(
                    landlord_interest_requests__bed__room_id=room_id,
                    landlord_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    landlord_interest_requests__is_active=True,
                    landlord_interest_requests__is_deleted=False,
                )
            )
            .distinct()
        )


        if tenants_for_room:
            send_onesignal_notification(
            tenant_ids=tenants_for_room,
            headings={"en": "Room details updated"},
            contents={"en": f"A landlord just updated details of a room"},
            data={"room_id": rt.id, "type": "tenant_update_property"},
            )
        return Response({"status": "success", "message": "Room saved.","roomId" : room_id if room_id != -1 else new_room.id}, status=200)

    except Exception as e:
        print("Error in update_landlord_room:", e)
        return Response({"status": "error", "message": str(e)}, status=500)


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_property_types_and_amenities(request):
    """
    API to fetch all active landlord property types and amenities.
    Optionally accepts a 'country_code' in the request params to retrieve the currency details,
    and a 'landlord_id' to check for base preferences.
    """
    # Step 1: Fetch all active property types
    property_types = LandlordPropertyTypeModel.objects.filter(is_active=True, is_deleted=False)
    
    # Step 2: Fetch all active amenities
    amenities = LandlordPropertyAmenityModel.objects.filter(is_active=True, is_deleted=False)

    # Step 3: Serialize them
    property_types_data = [
        {
            'id': pt.id,
            'type_name': pt.type_name,
            'description': pt.description
        }
        for pt in property_types
    ]
    amenities_data = [
        {
            'id': am.id,
            'name': am.name,
            'description': am.description
        }
        for am in amenities
    ]

    # Step 4: Optionally grab country for currency
    country_code = request.data.get("country_code", "").strip()
    currency_name = currency_symbol = ""
    if country_code:
        try:
            country = CountryModel.objects.get(iso2__iexact=country_code)
            currency_name = country.currency_name
            currency_symbol = country.currency_symbol
        except CountryModel.DoesNotExist:
            pass

    # Step 5: Check for base preferences
    landlord_id = request.data.get("landlord_id")
    found_base_pref = False
    if landlord_id is not None:
        found_base_pref = LandlordBasePreferenceModel.objects.filter(
            landlord_id=landlord_id
        ).exists()

    # Step 6: Build and return response
    resp = {
        "property_types":        property_types_data,
        "amenities":             amenities_data,
        "currency_name":         currency_name,
        "currency_symbol":       currency_symbol,
        "found_base_preference": True,
    }
    return Response(
        ResponseData.success(resp, "Property types and amenities fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_landlord_bed(request):
    """
    Request: one bed object in JSON.
     • bed_id = -1 → create; otherwise update that bed
     • room_id must always be present
    """
    try:
        data = request.POST
        # 1) validate room
        room_id = data.get("room_id")
        if not room_id:
            return Response({"status":"error","message":"Missing room_id."},
                            status=400)
        room = LandlordPropertyRoomDetailsModel.objects.filter(
            id=room_id
        ).first()
        if not room:
            return Response({"status":"error","message":"Room not found."},
                            status=404)

        # 2) parse JSON
        try:
            bd = json.loads(data.get("bed","{}"))
            print(f'finally_bed_details {bd}')
        except:
            return Response({"status":"error","message":"Invalid bed JSON."},
                            status=400)

        bed_id = bd.get("id", -1)
        # 3) update vs create
        if bed_id != -1:
            bed_obj, created = LandlordRoomWiseBedModel.objects.get_or_create(id=bed_id)
            dirty = False

            for key, fld in [
                ("rent_amount","rent_amount"),
                ("availability_start_date","availability_start_date"),
                ("is_rent_monthly","is_rent_monthly"),
                ("tenant_preference","tenant_preference"),
                ("min_agreement_duration_in_months","min_agreement_duration_in_months"),
            ]:
                if key in bd:
                    new_val = bd[key]
                    # coerce strings if necessary:
                    if fld == "rent_amount":
                        if new_val != '':
                            new_val = Decimal(new_val)
                    elif fld == "availability_start_date" and new_val:
                        new_val = new_val
                    if getattr(bed_obj, fld) != new_val:
                        setattr(bed_obj, fld, new_val)
                        dirty = True

            if dirty:
                bed_obj.save()
        else:
            if not bd.get("rent_amount"):
                return Response({"status":"error","message":"rent_amount required for new bed."}, status=400)
            answer_instances = []
            answer_instances = save_landlord_answers(bd,room.property.landlord,answer_instances)
            print(f'answer_instances {answer_instances}')
            bed_obj = LandlordRoomWiseBedModel.objects.create(
                room=room,
                bed_number=bd.get("bed_number"),
                tenant_preference=bd.get('tenant_preference') if bd.get('tenant_preference') is not None else '',
                is_available=bool(bd.get("availability_start_date")),
                rent_amount=bd["rent_amount"],
                availability_start_date=bd.get("availability_start_date") or None,
                is_rent_monthly=bd.get("is_rent_monthly", False),
                min_agreement_duration_in_months=(
                  0 if not bd.get("is_rent_monthly")
                  else bd.get("min_agreement_duration_in_months",0)
                )
            )
              # Use .set() AFTER creation
            if answer_instances:
                bed_obj.tenant_preference_answers.set(answer_instances)
            from .models import LandlordPropertyRoomTypeModel

            if room.room_type and room.room_type.type_name.lower() == "private":
                # count only non‐deleted beds
                current_beds = LandlordRoomWiseBedModel.objects.filter(
                    room=room,
                    is_deleted=False
                ).count()

                if current_beds > 1:
                    # find your "Sharing" room‐type record
                    sharing_type = LandlordPropertyRoomTypeModel.objects.get(
                        type_name__iexact="sharing",
                        is_active=True,
                        is_deleted=False
                    )
                    room.room_type = sharing_type
                    room.save(update_fields=["room_type"])
        tenants_for_bed = (
            TenantDetailsModel.objects
            .filter(
                # tenant-initiated interest
                Q(
                    tenant_interest_requests__bed_id=bed_id,
                    tenant_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    tenant_interest_requests__is_active=True,
                    tenant_interest_requests__is_deleted=False,
                )
                |
                # landlord-initiated interest
                Q(
                    landlord_interest_requests__bed_id=bed_id,
                    landlord_interest_requests__status__in=PENDING_OR_ACCEPTED,
                    landlord_interest_requests__is_active=True,
                    landlord_interest_requests__is_deleted=False,
                )
            )
            .distinct()
        )
        if tenants_for_bed:
            send_onesignal_notification(
            tenant_ids=tenants_for_bed,
            headings={"en": "Bed details updated"},
            contents={"en": f"A landlord just updated bed details"},
            data={"bed_id": bed_obj.id, "type": "tenant_update_property"},
            )
        return Response({"status":"success","message":"Bed saved."}, status=200)

    except Exception as e:
        print("Error in update_landlord_bed:", e)
        return Response({"status":"error","message":str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_properties(request):
    """
    API to fetch all properties for a landlord, including nested rooms & beds,
    plus for each bed a count of high_matches (>=40%) vs low_matches (<40%).
    Returns:
      {
        "success": true,
        "message": "...",
        "data": {
          "total_tenants": X,
          "properties": [ ... ]
        }
      }
    """
    serializer = PropertyListRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    landlord_id = serializer.validated_data['landlord_id']

    # fetch all props w/ rooms & beds
    props_qs = (
        LandlordPropertyDetailsModel.objects
          .filter(landlord_id=landlord_id, is_active=True, is_deleted=False)
          .select_related('property_city__state__country')
          .prefetch_related(
            Prefetch(
              'property_media',
              queryset=LandlordPropertyMediaModel.objects.filter(is_active=True, is_deleted=False)
            ),
            Prefetch(
              'rooms',
              queryset=(
                LandlordPropertyRoomDetailsModel.objects
                  .filter(is_deleted=False)
                  .prefetch_related(
                    Prefetch(
                      'beds',
                      queryset=LandlordRoomWiseBedModel.objects
                               .filter(is_active=True, is_deleted=False)
                    )
                  )
              )
            )
          )
    )

    all_tenant_ids = set()
    result = []

    for prop in props_qs:
        city = prop.property_city
        # gather tenants who prefer this city
        tenants = TenantDetailsModel.objects.filter(
            preferred_city=city,
            is_active=True, is_deleted=False
        )
        # collect unique for global total
        all_tenant_ids.update(tenants.values_list('id', flat=True))

        # for fallback:
        base_pref = LandlordBasePreferenceModel.objects.filter(
            landlord_id=landlord_id
        ).first()

        country = getattr(prop.property_city.state, 'country', None)
        currency_symbol = (
            country.currency_symbol
            if country and country.currency_symbol
            else (country.currency or '')
        )

        rooms_data = []
        for ridx, room in enumerate(prop.rooms.all()):
            beds_data = []
            for bed in room.beds.all():
                # compute high/low counters
                high = low = 0
                for tenant in tenants:
                    try:
                        persona = TenantPersonalityDetailsModel.objects.get(
                            tenant_id=tenant.id,
                            is_active=True, is_deleted=False
                        )
                    except TenantPersonalityDetailsModel.DoesNotExist:
                        persona = None

                    # get this tenant’s answers or fallback
                    lan = list(bed.tenant_preference_answers.all())
                    if not lan and base_pref:
                        lan = list(base_pref.answers.all())

                    overall_match, _ = compute_personality_match(persona, lan)
                    if overall_match >= 40:
                        high += 1
                    else:
                        low += 1

                period = "month" if bed.is_rent_monthly else "day"
                bed_dict = {
                    "id": bed.id,
                    "bed_number": f'{bed.room.room_name} Bed {bed.bed_number}',
                    "price": f"{currency_symbol} {bed.rent_amount} / {period}",
                    "type": "Private" if bed.is_rent_monthly else "Shared",
                    "is_rent_monthly": bed.is_rent_monthly,
                    "availability_start_date": (
                       bed.availability_start_date.isoformat()
                       if bed.availability_start_date else None
                    ),
                    # now two explicit counts:
                    "high_matches": high,
                    "low_matches": low,
                }
                beds_data.append(bed_dict)

            rooms_data.append({
                "id": room.id,
                "label": room.room_name.strip() or f"Room {ridx+1}",
                "beds": beds_data,
            })

        result.append({
            "id": prop.id,
            "name": prop.property_name,
            "size": prop.property_size,
            "type": prop.property_type.type_name if prop.property_type else None,
            "rooms": rooms_data,
        })

    return Response(
        ResponseData.success({
            "total_tenants": len(all_tenant_ids),
            "properties": result
        }, "Properties fetched successfully"),
        status=status.HTTP_200_OK
    )




@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_property_details(request):
    """
    API to fetch detailed information about a specific property.
    Expects POST request with {'landlord_id': int, 'property_id': int}
    """
    print(request.data)
    serializer = LandlordPropertyDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    landlord_id = serializer.validated_data['landlord_id']
    property_id = serializer.validated_data['property_id']

    property = LandlordPropertyDetailsModel.objects.filter(
        id=property_id,
        landlord_id=landlord_id,
        is_active=True,
        is_deleted=False
    ).prefetch_related(
        'property_media',
        'rooms__room_media',
        Prefetch(
            'rooms__beds',
            queryset=LandlordRoomWiseBedModel.objects.filter(is_deleted=False)  # Only active beds
            .order_by('bed_number')
            .prefetch_related('bed_media', 'tenant_preference_answers')
        )
    ).first()

    if not property:
        return Response(
            ResponseData.error("Property not found or inactive"),
            status=status.HTTP_404_NOT_FOUND
        )
    country = getattr(property.property_city.state, 'country', None)
    currency_symbol = (
        country.currency_symbol
        if country and country.currency_symbol
        else (country.currency or '')
    )
    # STEP 1: Fetch all active property types
    property_types = LandlordPropertyTypeModel.objects.filter(is_active=True, is_deleted=False)
    
    # STEP 2: Fetch all active amenities
    amenities = LandlordPropertyAmenityModel.objects.filter(is_active=True, is_deleted=False)

    # STEP 3: Prepare response data
    property_types_data = [
        {
            'id': property_type.id,
            'type_name': property_type.type_name,
            'description': property_type.description
        }
        for property_type in property_types
    ]

    amenities_data = [
        {
            'id': amenity.id,
            'name': amenity.name,
            'description': amenity.description
        }
        for amenity in amenities
    ]

    # STEP 4: Serialize response data
    response_serializer = LandlordPropertyDetailSerializer(
        property,
        context={'property_types': property_types_data, 'amenities': amenities_data}
    )

    response_data = response_serializer.data  # Get serialized data as a dictionary
    response_data['currency_symbol'] = currency_symbol
    # ─── NEW: sort the rooms list by room “id” ───
    response_data['rooms'] = sorted(
        response_data.get('rooms', []),
        key=lambda room: room['id']
    )
    # STEP 5: Convert `property_media` to list of file URLs
    response_data["property_media"] = [
        media["file"] for media in response_data.get("property_media", [])
    ]

    # STEP 6: Convert `room_media` and `bed_media` to list of file URLs
    for room_index, room in enumerate(response_data.get('rooms', [])):
        # Convert room_media => list of files
        room["room_media"] = [
            media["file"] for media in room.get("room_media", [])
        ]

        for bed_index, bed in enumerate(room.get('beds', [])):
            # Convert bed_media => list of files
            bed["bed_media"] = [
                media["file"] for media in bed.get("bed_media", [])
            ]

    # STEP 7: (Example) Modify response to group tenant_preference_answers
    for room_index, room in enumerate(response_data.get('rooms', [])):
        print(f'checkroom {room}')
        room["is_active"] = room.get('is_active')
        for bed_index, bed in enumerate(room.get('beds', [])):
            
            tenant_answers = bed.get('tenant_preference_answers', [])
            if len(tenant_answers) != 0:
                bed['bed_tenant_preference'] = f"Room {room_index + 1} Bed {bed_index + 1} Preference"
            grouped_answers = {}
            for answer in tenant_answers:
                print(f'answer {answer}')
                question_id = answer["question"]["id"]
                option_id = answer["object_id"] if answer["object_id"] else None
                preference = answer["preference"]
                
                if option_id is None:
                    continue

                if question_id not in grouped_answers:
                    grouped_answers[question_id] = {
                        "question_id": question_id,
                        "selected_option_indices": [],
                        "priority_order": [],
                        "unselected_indices": [],
                    }

                if preference is not None:
                    grouped_answers[question_id]["selected_option_indices"].append(option_id)
                    grouped_answers[question_id]["priority_order"].append(option_id)
                question = LandlordQuestionModel.objects.filter(
                        id=question_id,
                        is_active=True, 
                        is_deleted=False
                    ).select_related('question_type').prefetch_related('content_type').first()
                content_model = question.content_type.model_class() if question.content_type else None
                
                # Fetch options for the related model (like OccupationModel or any other model)
                if content_model:
                    all_option_ids = content_model.objects.filter(is_active=True, is_deleted=False).values_list("id", flat=True)
                        
                print(f'all_option_ids {all_option_ids}')
                print(f'grouped_answers {grouped_answers}')
                grouped_answers[question_id]["selected_option_indices"] = [
                    d["id"] if isinstance(d, dict) else d
                    for d in grouped_answers[question_id]["selected_option_indices"]
                ]

                grouped_answers[question_id]["priority_order"] = [
                    d["id"] if isinstance(d, dict) else d
                    for d in grouped_answers[question_id]["priority_order"]
                ]

                selected_options = set(grouped_answers[question_id]["selected_option_indices"])

                grouped_answers[question_id]["unselected_indices"] = [
                    option for option in all_option_ids if option not in selected_options
                ]

            bed["tenant_preference_answers"] = list(grouped_answers.values())
            bed["is_active"] = bed.get('is_active')
    print(f'response_data {response_data}')
    # STEP 8: Return final response
    return Response(
        ResponseData.success(response_data, "Property details fetched"),
        status=status.HTTP_200_OK
    )


def build_all_tabs(property_id):
    """
    Returns a list of dictionaries representing 'tabs' similar to the Dart logic:
    1) One tab for the property itself.
    2) One tab for each room.
    3) If the room is not private (replace with your actual logic), 
       and it has beds, one tab for each bed.
    """
    tabs = []
    try:
        # Fetch the property
        property_obj = LandlordPropertyDetailsModel.objects.get(id=property_id, is_active=True, is_deleted=False)

        # 2) For each room, add a tab
        rooms = property_obj.rooms.filter(is_active=True, is_deleted=False)
        for i, room in enumerate(rooms, start=1):
            # 3) If the room is not private and has beds, add tabs for each bed
            # (Adjust "room.is_private" below to match your real field/logic)
            if hasattr(room, 'is_private'):
                is_room_private = room.is_private
            else:
                # If there's no 'is_private', set default or skip
                is_room_private = False

            if not is_room_private and room.beds.exists():
                beds_qs = room.beds.filter(is_active=True, is_deleted=False)
                for bed_index, bed in enumerate(beds_qs, start=1):
                    tabs.append({
                        "title": f"Room {i} - Bed {bed_index}",
                        "bed_id": bed.id
                    })
            if is_room_private and room.beds.exists():
                    tabs.append({
                        "title": f"Room {i} - Bed 1",
                        "bed_id": bed.id
                    })
        return tabs
    except LandlordPropertyDetailsModel.DoesNotExist:
        # If the property doesn't exist, return empty or handle error
        return []


'''@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_property_details(request):
    """
    Returns top‑level property info plus a flat list of its rooms (no nested beds).
    """
    serializer = LandlordPropertyDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors), status=400)

    landlord_id = serializer.validated_data['landlord_id']
    property_id = serializer.validated_data['property_id']

    prop = (
      LandlordPropertyDetailsModel.objects
        .filter(id=property_id, landlord_id=landlord_id, is_active=True, is_deleted=False)
        .prefetch_related('property_media')
        .first()
    )
    if not prop:
        return Response(ResponseData.error("Property not found or inactive"), status=404)

    # property types & amenities
    ptypes = LandlordPropertyTypeModel.objects.filter(is_active=True, is_deleted=False)
    amens  = LandlordPropertyAmenityModel.objects.filter(is_active=True, is_deleted=False)

    data = {
      "id":                prop.id,
      "property_name":     prop.property_name,
      "property_size":     prop.property_size,
      "property_description": prop.property_description,
      "floor":             prop.floor,
      "number_of_rooms":   prop.number_of_rooms,
      "property_media":    [m.file.url for m in prop.property_media.all()],
      "property_types": [
         {"id":t.id, "type_name":t.type_name, "description":t.description}
         for t in ptypes
      ],
      "amenities": [
         {"id":a.id, "name":a.name, "description":a.description}
         for a in amens
      ],
      "rooms": [
        {
          "id":            r.id,
          "room_type":     r.room_type_id,
          "room_size":     r.room_size,
          "is_active":     r.is_active
        }
        for r in prop.rooms.filter(is_deleted=False)
      ]
    }

    return Response(ResponseData.success(data, "Property details fetched"), status=200)
'''
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_room_details(request):
    """
    Returns one room’s full detail plus a flat list of its beds (no nested preferences).
    If the room_type is “Private”, also include the room’s `available_from` date,
    taken from its first (and only) bed’s availability_start_date.
    """
    serializer = LandlordRoomDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors), status=400)

    ld, pid, rid = (
        serializer.validated_data['landlord_id'],
        serializer.validated_data['property_id'],
        serializer.validated_data['room_id'],
    )

    room = (
        LandlordPropertyRoomDetailsModel.objects
            .filter(
                id=rid,
                property__id=pid,
                property__landlord_id=ld,
                is_deleted=False
            )
            .prefetch_related('room_media', 'beds')
            .first()
    )
    if not room:
        return Response(ResponseData.error("Room not found"), status=404)

    # base payload
    data = {
        "id":                   room.id,
        "room_type":            room.room_type_id,
        "room_size":            room.room_size,
        'room_name' : room.room_name if room.room_name else '',
        "location_in_property": room.location_in_property,
        "number_of_beds":       room.number_of_beds,
        "number_of_windows":    room.number_of_windows,
        "max_people_allowed":   room.max_people_allowed,
        "current_male_occupants":   room.current_male_occupants,
        "current_female_occupants":   room.current_female_occupants,
        "floor":                room.floor,
        "is_active":            room.is_active,
        "room_media": [
            {
                "id":         m.id,
                "file":       m.file.url,
                "media_type": m.media_type,
            }
            for m in room.room_media.all()
        ],
        "beds": [
            {
                "id":         b.id,
                "bed_number": f'{b.room.room_name} Bed {b.bed_number}',
                "is_active":  b.is_active,
                "tenant_preference" : b.tenant_preference,
                "price" : b.rent_amount,
            }
            for b in room.beds.filter(is_deleted=False).order_by('id') 
        ],
    }

    # --- new block: if this is a Private room, pull in its bed's availability ---
    if room.room_type and room.room_type.type_name.lower() == "private":
        # pick the first non-deleted bed
        first_bed = room.beds.filter(is_deleted=False).first()
        if first_bed and hasattr(first_bed, 'availability_start_date') and hasattr(first_bed, 'rent_amount'):
            # if it's a DateField, convert to ISO; if already string, keep as-is
            ava = first_bed.availability_start_date
            data['rent_amount'] = str(first_bed.rent_amount)
            if first_bed.min_agreement_duration_in_months is not None:
                data['min_agreement_duration'] = int(first_bed.min_agreement_duration_in_months)
            data["availability_start_date"] = (
                ava.isoformat() if hasattr(ava, "isoformat") else str(ava)
            )
    rooms = (
        LandlordPropertyRoomDetailsModel.objects
        .filter(property__id=pid,
                property__landlord_id=ld,
                is_deleted=False)
        .prefetch_related('beds')
    )
    data["all_preferences"] = build_all_preferences(rooms,ld)

    return Response(ResponseData.success(data, "Room details fetched"), status=200)

def build_all_preferences(rooms, landlord):
    """
    Given:
      - rooms: iterable of Room instances (each with a reverse .beds relation)
      - landlord: a LandlordDetailsModel instance
    Returns a de-duplicated list of dicts:
      { 'bed_id': <id>, 'tenant_preference': <str> }
    for every bed whose .tenant_preference is non-empty, plus one
    entry for the landlord’s global (base) preference if it exists.
    """
    all_prefs = []
    seen = set()

    # 1) per-bed preferences
    for room in rooms:
        for bed in room.beds.filter(is_deleted=False):
            tp = (bed.tenant_preference or "").strip()
            if tp and tp not in seen:
                seen.add(tp)
                all_prefs.append({
                    "bed_id": bed.id,
                    "tenant_preference": tp,
                })

    if LandlordBasePreferenceModel.objects.filter(landlord=landlord).exists():
        # only add once, and only if not already captured
        base_tp = "Base Preference"
        if base_tp not in seen:
            all_prefs.append({
                "bed_id": -1,
                "tenant_preference": base_tp,
            })

    return all_prefs

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_bed_details(request):
    serializer = LandlordBedDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors), status=400)

    ld, pid, rid, bid = (
        serializer.validated_data['landlord_id'],
        serializer.validated_data['property_id'],
        serializer.validated_data['room_id'],
        serializer.validated_data['bed_id'],
    )

    bed = (
        LandlordRoomWiseBedModel.objects
        .filter(
            id=bid,
            room__id=rid,
            room__property__id=pid,
            room__property__landlord_id=ld,
            is_deleted=False
        )
        # make sure we have media and answers/question prefetched
        .prefetch_related('bed_media', 'tenant_preference_answers__question')
        .first()
    )
    if not bed:
        return Response(ResponseData.error("Bed not found"), status=404)

    # --- CHANGE HERE ---
    bed_media = [
        {
            "id": m.id,
            "file": m.file.url,
            "media_type": m.media_type,
        }
        for m in bed.bed_media.all()
    ]
    # ---------------------
    print(f'bed.tenant_preference {bed.tenant_preference}')

    data = {
        "id": bed.id,
        "bed_number": f'{bed.room.room_name} Bed {bed.bed_number}',
        "rent_amount": str(bed.rent_amount),
        "availability_start_date": (
            bed.availability_start_date.isoformat()
            if bed.availability_start_date else None
        ),
        "is_rent_monthly": bed.is_rent_monthly,
        "min_agreement_duration_in_months": bed.min_agreement_duration_in_months,
        "is_active": bed.is_active,
        "bed_media": bed_media,                     # now a list of maps
        "tenant_preference" : bed.tenant_preference
    }
    rooms = (
        LandlordPropertyRoomDetailsModel.objects
        .filter(property__id=pid,
                property__landlord_id=ld,
                is_deleted=False)
        .prefetch_related('beds')
    )

    data["all_preferences"] = build_all_preferences(rooms,ld)
    print(f'data["all_preferences"] {data["all_preferences"]}')
    return Response(
        ResponseData.success(data, "Bed details fetched"),
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_profile_details(request):
    """
    API to fetch landlord profile details.
    Expects a POST request with 'landlord_id' in the request data.
    Returns basic landlord profile data along with profile completion percentage.
    """
    # Step 1: Validate request data
    serializer = LandlordProfileRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    landlord_id = serializer.validated_data.get("landlord_id")
    
    # Step 2: Fetch landlord details
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 3: Build landlord basic profile data
    landlord_data = {
        "id": landlord.id,
        "first_name": landlord.first_name,
        "last_name": landlord.last_name,
        "email": landlord.email,
        "phone_number": landlord.phone_number,
        "date_of_birth": landlord.date_of_birth.strftime("%Y-%m-%d") if landlord.date_of_birth else None,
        "profile_picture": landlord.profile_picture.url if landlord.profile_picture else None,
    }
    
    # Step 4: Calculate profile completion percentage.
    # We consider 3 fields: phone_number, date_of_birth, profile_picture.
    total_fields = 3
    filled_fields = sum([
        1 if landlord.phone_number else 0,
        1 if landlord.date_of_birth else 0,
        1 if landlord.profile_picture else 0,
    ])
    profile_completion = int((filled_fields / total_fields) * 100)
    
    # Step 5: Prepare full response data
    data = {
        "landlord": landlord_data,
        "profile_completion": profile_completion,
    }
    
    return Response(
        ResponseData.success(data, "Landlord profile fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def update_profile_details(request):
    """
    API to update landlord profile details.
    Expects a POST request with 'landlord_id' and other profile fields.
    """
    print(f'request.data {request.data}')
    serializer = UpdateLandlordProfileSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id = serializer.validated_data.get("landlord_id")
    
    # Fetch landlord details
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update landlord details

    landlord.phone_number = serializer.validated_data.get("phone_number", landlord.phone_number)
    if "date_of_birth" in request.data:
        landlord.date_of_birth = serializer.validated_data.get("date_of_birth", landlord.date_of_birth)
    
    # Handle profile picture update
    if "profile_picture" in request.FILES:
        landlord.profile_picture = request.FILES["profile_picture"]
    
    landlord.save()
    
    return Response(
        ResponseData.success_without_data("Landlord profile updated successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_identity_document(request):
    print(f'request.data {request.data}')
    serializer = AddIdentityDocumentSerializer(data=request.data)
    if serializer.is_valid():
        landlord_id = serializer.validated_data['landlord_id']
        document_type_id = serializer.validated_data['document_type']
        document_number = serializer.validated_data.get('document_number', '')
        files = request.FILES.getlist('document_files')
        # Create a new identity document record
        identity_doc = LandlordIdentityVerificationModel.objects.create(
            landlord_id=landlord_id,
            document_type_id=document_type_id,
            document_number=document_number,
            submitted_at=now(),
            verification_status='pending'
        )
        # Create file records for each file uploaded
        for file in files:
            LandlordIdentityVerificationFile.objects.create(
                identity_document=identity_doc,
                file=file,
                uploaded_at=now()
            )
        return Response(
            ResponseData.success_without_data("Identity document added successfully."),
            status=status.HTTP_201_CREATED
        )
    return Response(ResponseData.error(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_all_identity_documents(request):
    landlord_id = request.data.get('landlord_id')
    if not landlord_id:
        return Response(
            ResponseData.error("landlord_id parameter is required."),
            status=status.HTTP_400_BAD_REQUEST
        )
    documents = LandlordIdentityVerificationModel.objects.filter(
        landlord_id=landlord_id, is_active=True, is_deleted=False
    )
    document_serializer = LandlordIdentityDocumentSerializer(
        documents, many=True, context={'request': request}
    )
    
    document_types = LandlordDocumentTypeModel.objects.filter(is_active=True, is_deleted=False)
    doc_types_serializer = LandlordDocumentTypeSerializer(
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
        document = LandlordIdentityVerificationModel.objects.get(id=doc_id, is_active=True, is_deleted=False)
    except LandlordIdentityVerificationModel.DoesNotExist:
        return Response(ResponseData.error("Document not found."), status=status.HTTP_404_NOT_FOUND)

    # Extract request data
    document_type_id = request.data.get('document_type')
    document_number = request.data.get('document_number')
    # Ensure document_number uniqueness check is bypassed for the same document
    if document_number and document_number != document.document_number:
        if LandlordIdentityVerificationModel.objects.filter(document_number=document_number).exclude(id=doc_id).exists():
            return Response(ResponseData.error("Document number already exists."), status=status.HTTP_400_BAD_REQUEST)

    # Update only fields that are present in the request
    if document_type_id:
        try:
            document_type = LandlordDocumentTypeModel.objects.get(id=document_type_id)
            document.document_type = document_type
        except LandlordDocumentTypeModel.DoesNotExist:
            return Response(ResponseData.error("Invalid document type."), status=status.HTTP_400_BAD_REQUEST)

    if document_number:
        document.document_number = document_number
        document.verification_status = 'pending'

    document.save()

    # Handle file uploads if new files are provided
    # Fetch existing files from the LandlordIdentityVerificationFile table
    existing_files = LandlordIdentityVerificationFile.objects.filter(identity_document=document)

    # Create a set of existing file names
    existing_file_names = {os.path.basename(file_obj.file.name) for file_obj in existing_files}

    # Get new uploaded files
    new_files = request.FILES.getlist('document_files')

    # Convert new file names into a set for comparison
    new_file_names = {file.name for file in new_files}

    # Identify files to delete (existing files not present in new uploads)
    files_to_delete = existing_files.exclude(file__in=[f'static/landlord_identity_documents/{name}' for name in new_file_names])

    # Delete missing files from the database and storage
    for file_obj in files_to_delete:
        
        # Delete from file system
        os.remove(file_obj.file.name)
        
        # Delete from database
        file_obj.delete()

    # Add only new files (avoid re-adding existing ones)
    for file in new_files:
        if file.name not in existing_file_names:
            LandlordIdentityVerificationFile.objects.create(
                identity_document=document,
                file=file,
                uploaded_at=now()
            )


    return Response(ResponseData.success_without_data("Identity document updated successfully."), status=status.HTTP_200_OK)

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_identity_document(request):
    doc_id = request.data.get('id')
    if not doc_id:
        return Response(ResponseData.error("Document id is required."), status=status.HTTP_400_BAD_REQUEST)
    try:
        document = LandlordIdentityVerificationModel.objects.get(id=doc_id, is_active=True, is_deleted=False)
    except LandlordIdentityVerificationModel.DoesNotExist:
        return Response(ResponseData.error("Document not found."), status=status.HTTP_404_NOT_FOUND)
    document.is_deleted = True
    document.deleted_at = now()
    document.save()
    return Response(ResponseData.success_without_data("Identity document deleted successfully."), status=status.HTTP_200_OK)

import os
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_landlord_media_selection(request):
    try:
        print("Received Request: Processing...")

        # Debug: Print incoming POST data
        try:
            for key, value in request.POST.items():
                print(f"POST Key: {key} | Value: {value}")
        except Exception as e:
            print(f"Error reading request.POST data: {str(e)}")
            return Response({'error': 'Error reading request data'}, status=status.HTTP_400_BAD_REQUEST)

        # Debug: Print uploaded files
        try:
            for key, file in request.FILES.items():
                print(f"File Received - Key: {key} | Name: {file.name}")
        except Exception as e:
            print(f"Error reading uploaded files: {str(e)}")
            return Response({'error': 'Error reading uploaded files'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract data from request
        try:
            landlord_id = request.POST.get('landlord_id')
            property_id = request.POST.get('property_id')
            is_for_property = request.POST.get('isForProperty') == "true"
            is_for_room = request.POST.get('isForRoom') == "true"
            is_for_bed = request.POST.get('isForBed') == "true"
            room_index = request.POST.get('roomIndex', '0')
            bed_index = request.POST.get('bedIndex', '0')
            is_added = request.POST.get('is_added', True)

            if not landlord_id:
                print("Error: Missing landlord_id")
                return Response({'error': 'Missing landlord_id'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error extracting form data: {str(e)}")
            return Response({'error': 'Error extracting form data'}, status=status.HTTP_400_BAD_REQUEST)

        # Define base directory inside temp_landlord_data
        try:
            base_dir = os.path.join(settings.MEDIA_ROOT, 'temp_landlord_data', f"landlord_{landlord_id}")
            print(f"Base Directory: {base_dir}")

            # Determine the upload directory based on file type
            if is_for_property:
                upload_dir = os.path.join(base_dir, "property")
            elif is_for_room:
                upload_dir = os.path.join(base_dir, f"room_{room_index}")
            elif is_for_bed:
                upload_dir = os.path.join(base_dir, f"room_{room_index}", f"bed_{bed_index}")
            else:
                print("Error: Invalid media type")
                return Response({'error': 'Invalid media type'}, status=status.HTTP_400_BAD_REQUEST)
            print(f'is_added {is_added}')
            if is_added == 'true':
            # Create directories if they do not exist
                os.makedirs(upload_dir, exist_ok=True)
            else:
                try:
                    for file_key, file_obj in request.FILES.items():
                        print(f'is_added {is_added} {upload_dir} {file_obj.name}')
                        file_path = os.path.join(upload_dir, file_obj.name)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"Deleted file: {file_path}")
                    return Response({'message': 'Files deleted successfully'}, status=status.HTTP_200_OK)
                except Exception as e:
                    print(f"Error deleting files: {str(e)}")
                    return Response({'error': f'Error deleting files: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            print(f"Upload Directory Created: {upload_dir}")
        except Exception as e:
            print(f"Error creating directories: {str(e)}")
            return Response({'error': 'Error creating directories'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle file upload
        uploaded_files = []
        try:
            for file_key, file_obj in request.FILES.items():
                file_path = os.path.join(upload_dir, file_obj.name)

                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)

                uploaded_files.append(file_path)
                print(f"File Saved: {file_path}")
        except Exception as e:
            print(f"Error saving file {file_obj.name}: {str(e)}")
            return Response({'error': f'Error saving file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print("File Upload Successful!")
        return Response({'message': 'Files uploaded successfully'}, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"General Error in Upload API: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def update_uploaded_landlord_media_selection(request):
    try:
        # Log incoming POST data for debugging.
        for key, value in request.POST.items():
            print(f"POST Key: {key} | Value: {value}")
        for key, file in request.FILES.items():
            print(f"File Received - Key: {key} | Name: {file.name}")

        # Extract required fields.
        landlord_id = request.POST.get('landlord_id')
        property_id = int(request.POST.get('property_id'))
        room_id = int(request.POST.get('room_id', '0'))
        bed_id = int(request.POST.get('bed_id', '0'))
        is_added = request.POST.get('is_added', True)

        if not landlord_id or not property_id:
            return Response({'error': 'Missing landlord_id or property_id'}, status=status.HTTP_400_BAD_REQUEST)

        # This API is for updating an existing property. 
        # If property_id equals "-1", that's new property mode—use your other API.
        if property_id == -1:
            return Response({'error': 'This endpoint is only for updating existing property media.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validate that the property exists.
        try:
            property_instance = LandlordPropertyDetailsModel.objects.get(
                id=property_id, is_deleted=False, is_active=True
            )
        except LandlordPropertyDetailsModel.DoesNotExist:
            return Response({'error': 'Property not found or inactive.'}, status=status.HTTP_404_NOT_FOUND)


        # We'll demonstrate for property media (images and videos).
        # For other types (room/bed), the logic is analogous with their respective models.

            # Process images.
        uploaded_files = []
        print(f'property_id {property_id}')
        print(f'room_id {type(room_id)}')
        print(f'bed_id {bed_id}')
        for file_key, file_obj in request.FILES.items():
            file_name = file_obj.name
            media_type = get_media_type(file_name)
            # Look for an existing media record for this property & image.
            if property_id != -1 and room_id == -1 and bed_id == -1:
                print('entered_1')
                existing = LandlordPropertyMediaModel.objects.filter(
                    property=property_instance,
                    media_type=media_type,
                    file__icontains=file_name
                ).first()
            elif room_id != -1:
                room_instance = LandlordPropertyRoomDetailsModel.objects.get(
                id=room_id, is_deleted=False, is_active=True
            )
                existing = LandlordRoomMediaModel.objects.filter(
                    room=room_instance,
                    media_type=media_type,
                    file__icontains=file_name
                ).first()
            elif bed_id != -1:
                bed_instance = LandlordRoomWiseBedModel.objects.get(
                id=bed_id, is_deleted=False, is_active=True
            )
                existing = LandlordBedMediaModel.objects.filter(
                    bed=bed_instance,
                    media_type=media_type,
                    file__icontains=file_name
                ).first()
            if is_added == 'true':
                print('entered_2')
                if existing:
                    # If record exists, activate it and update file if needed.
                    existing.is_active = True
                    existing.is_deleted = False
                    existing.save()
                    uploaded_files.append(existing.file.url)
                    print(f"Updated existing image: {file_name} as active.")
                else:
                    print('entered_3')
                    if property_id != -1 and room_id == -1 and bed_id == -1:
                        print('entered_4')
                        new_media = LandlordPropertyMediaModel.objects.create(
                            property=property_instance,
                            file=file_obj,
                            media_type=media_type
                        )
                        uploaded_files.append(new_media.file.url)
                        print(f"Created new image: {file_name}")
                    if room_id != -1:
                        new_media = LandlordRoomMediaModel.objects.create(
                            room=room_instance,
                            file=file_obj,
                            media_type=media_type
                        )
                        uploaded_files.append(new_media.file.url)
                        print(f"Created new image: {file_name}")
                    if bed_id != -1:
                        new_media = LandlordBedMediaModel.objects.create(
                            bed=bed_instance,
                            file=file_obj,
                            media_type=media_type
                        )
                        uploaded_files.append(new_media.file.url)
                        print(f"Created new image: {file_name}")
            else:  # is_added is "false" => Mark as deleted.
                if existing:
                    existing.is_active = False
                    existing.is_deleted = True
                    existing.save()
                    print(f"Marked property image {file_name} as deleted.")
                    uploaded_files.append(file_name)
            return Response(
                {
                    'message': 'Property media updated successfully.',
                },
                status=status.HTTP_200_OK
            )
        else:
            # Implement similar logic for room and bed media here.
            return Response({'message': 'This endpoint currently handles only property media.'},
                            status=status.HTTP_200_OK)

    except Exception as e:
        print(f"General Error in Update Media API: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def toggle_active_status(request):
    """
    API to update the is_active status of a room or bed.
    Expects a POST request with either 'room_id' or 'bed_id'. 
    For a room update, room_id should not be -1.
    For a bed update, bed_id should not be -1.
    The operation toggles the is_active boolean.
    """
    print(f'request.params {request.data}')
    serializer = ToggleActiveStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    room_id = serializer.validated_data.get("room_id", -1)
    bed_id = serializer.validated_data.get("bed_id", -1)

    if room_id != -1 and bed_id == -1:
        room = LandlordPropertyRoomDetailsModel.objects.filter(
            id=room_id, is_deleted=False
        ).first()
        if not room:
            return Response(
                ResponseData.error("Invalid room ID."),
                status=status.HTTP_400_BAD_REQUEST
            )
        # Toggle is_active value
        room.is_active = not room.is_active
        room.save()
    elif room_id != -1 and bed_id != -1:
        bed = LandlordRoomWiseBedModel.objects.filter(
            id=bed_id, is_deleted=False
        ).first()
        if not bed:
            return Response(
                ResponseData.error("Invalid bed ID."),
                status=status.HTTP_400_BAD_REQUEST
            )
        # Toggle is_active value
        bed.is_active = not bed.is_active
        bed.save()
    else:
        return Response(
            ResponseData.error("Either a valid room_id or bed_id is required."),
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        ResponseData.success_without_data("State updated successfully."),
        status=status.HTTP_200_OK
    )
    
@api_view(['POST'])
@parser_classes([JSONParser])
def save_landlord_base_preferences(request):
    """
    Save or update a landlord’s *global* (base) tenant-preference answers,
    then propagate them to every bed (creating or updating each LandlordRoomWiseBedModel).
    """
    serializer = LandlordBasePreferenceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id = serializer.validated_data['user_id']
    answers = serializer.validated_data['answers']

    # 1) validate landlord
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord_id or landlord not active."),
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) get-or-create the base-preference record
    base_pref, _ = LandlordBasePreferenceModel.objects.get_or_create(
        landlord=landlord
    )

    # 3) upsert answers & collect their IDs
    answer_ids = []
    for ans in answers:
        q_id = ans.get("question_id")
        prios = ans.get("priority_order", [])

        # validate question
        question = LandlordQuestionModel.objects.filter(
            id=q_id, is_active=True, is_deleted=False
        ).first()
        if not question:
            return Response(
                ResponseData.error(f"Invalid question_id: {q_id}"),
                status=status.HTTP_400_BAD_REQUEST
            )

        ct = question.content_type
        if not ct:
            return Response(
                ResponseData.error(f"Question {q_id} has no content_type defined."),
                status=status.HTTP_400_BAD_REQUEST
            )

        for preference, option_id in enumerate(prios, start=1):
            answer_obj, _ = LandlordAnswerModel.objects.update_or_create(
                landlord=landlord,
                question=question,
                content_type=ct,
                object_id=option_id,
                preference=preference,
                defaults={
                    "preference": preference,
                    "is_active": True,
                    "is_deleted": False,
                },
            )
            answer_ids.append(answer_obj.id)

    # 4) replace the M2M set on the base‐preference record
    base_pref.answers.set(answer_ids)

    # 5) propagate to every bed:
    # 5) propagate to every existing bed:
    for prop in landlord.properties.filter(is_active=True, is_deleted=False):
        for room in prop.rooms.filter(is_active=True, is_deleted=False):
            # only update beds that already have a record
            existing_beds = LandlordRoomWiseBedModel.objects.filter(
                room=room,
                is_active=True,
                is_deleted=False
            )
            for bed_instance in existing_beds:
                bed_instance.tenant_preference_answers.set(answer_ids)

    return Response(
        ResponseData.success_without_data("Base tenant preferences saved and applied to all beds."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def get_all_preferences_of_property(request):
    """
    Returns a de-duplicated flat list of every bed’s tenant_preference
    for all rooms in the given property, plus one “base” entry if set.
    """
    req_s = PropertyAllPreferencesRequestSerializer(data=request.data)
    if not req_s.is_valid():
        return Response(ResponseData.error(req_s.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    landlord_id = req_s.validated_data["landlord_id"]
    property_id = req_s.validated_data["property_id"]

    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(ResponseData.error("Invalid landlord_id"),
                        status=status.HTTP_400_BAD_REQUEST)

    prop = LandlordPropertyDetailsModel.objects.filter(
        id=property_id,
        landlord=landlord,
        is_active=True,
        is_deleted=False
    ).first()
    if not prop:
        return Response(ResponseData.error("Property not found"), status=404)

    # collect rooms + their beds
    rooms = prop.rooms.filter(is_active=True, is_deleted=False) \
               .prefetch_related("beds")

    all_prefs = []
    seen = set()

    # 1) per-bed prefs
    for room in rooms:
        for bed in room.beds.filter(is_deleted=False, is_active=True):
            tp = (bed.tenant_preference or "").strip()
            if tp and tp not in seen:
                seen.add(tp)
                all_prefs.append({
                    "bed_id": bed.id,
                    "tenant_preference": tp,
                })

    # 2) global/base preferences?
    if LandlordBasePreferenceModel.objects.filter(landlord=landlord).exists():
        base_label = "Base Preference"
        if base_label not in seen:
            all_prefs.append({
                "bed_id": -1,
                "tenant_preference": base_label,
            })

    return Response(
        ResponseData.success(
            all_prefs,
            "All preferences fetched"
        ),
        status=status.HTTP_200_OK
    )
    
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def check_property_exists(request):
    """
    Check if a property with the given lat, lng and street_number exists.
    """
    print(f'check_property_exists_request {request.data}')
    serializer = CheckPropertyExistsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    raw_lat    = serializer.validated_data['latitude']
    raw_lng    = serializer.validated_data['longitude']
    number = serializer.validated_data['street_number'].strip()

    # 2. Define a quantizer for exactly 8 decimal places
    eight_places = Decimal('0.' + '0' * 7 + '1')      # Decimal('0.00000001')

    # 3. Quantize (pad) each value
    lat = raw_lat.quantize(eight_places, rounding=ROUND_HALF_UP)
    lng = raw_lng.quantize(eight_places, rounding=ROUND_HALF_UP)
    # now lat == Decimal('52.41991520'), lng == Decimal('13.32132260')
    print(f'lat {lat}')
    print(f'lng {lng}')
    # 4. Use those padded values in your query
    exists = LandlordPropertyDetailsModel.objects.filter(
        latitude=lat,
        longitude=lng,
        street_number__iexact=number,
        is_active=True,
        is_deleted=False
    ).exists()
    print(f'existssvsvsd {exists}')

    return Response(
        ResponseData.success(exists,'This address already exists'),
        status=status.HTTP_200_OK
    )