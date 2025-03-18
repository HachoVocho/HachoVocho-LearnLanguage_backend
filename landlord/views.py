import json
import os
import re
import shutil
from rest_framework.decorators import api_view,parser_classes
from rest_framework.response import Response
from rest_framework import status
from localization.models import CityModel, CountryModel
from tenant.models import TenantDetailsModel
from response import Response as ResponseData
from .models import LandlordBedMediaModel, LandlordDetailsModel, LandlordDocumentTypeModel, LandlordEmailVerificationModel, LandlordIdentityVerificationFile, LandlordIdentityVerificationModel, LandlordOptionModel, LandlordPropertyAmenityModel, LandlordPropertyDetailsModel, LandlordPropertyMediaModel, LandlordPropertyRoomDetailsModel, LandlordPropertyRoomTypeModel, LandlordPropertyTypeModel, LandlordQuestionModel, LandlordRoomMediaModel
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils.timezone import now
import random
from django.core.files import File
from django.db.models import Prefetch
from django.contrib.contenttypes.models import ContentType
from .models import LandlordQuestionModel, LandlordAnswerModel, LandlordRoomWiseBedModel
from .serializers import AddIdentityDocumentSerializer, LandlordDocumentTypeSerializer, LandlordIdentityDocumentSerializer, LandlordPreferenceAnswerSerializer, LandlordProfileRequestSerializer, LandlordPropertyDetailRequestSerializer, LandlordPropertyDetailSerializer, LandlordQuestionRequestSerializer, LandlordSignupSerializer, PropertyListRequestSerializer, TenantInterestRequestSerializer, ToggleActiveStatusSerializer, UpdateLandlordProfileSerializer
from rest_framework.parsers import MultiPartParser, FormParser

@api_view(["POST"])
def landlord_signup(request):
    """API to handle landlord signup"""
    try:
        serializer = LandlordSignupSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            tenant = TenantDetailsModel.objects.filter(email=email,is_active=True).first()
            if tenant is not None:
                return Response(
                    ResponseData.error("This email already exists for tenant"),
                    status=status.HTTP_200_OK
                )
            # Check if the email already exists in LandlordDetailsModel
            landlord = LandlordDetailsModel.objects.filter(email=email).first()

            if landlord:
                # If landlord exists, check for an ongoing OTP verification
                landlord_verification = LandlordEmailVerificationModel.objects.filter(
                    landlord=landlord, is_verified=False
                ).first()

                if landlord_verification:
                    # If OTP exists but not verified, generate a new OTP and send it
                    otp = str(random.randint(100000, 999999))  # Generate a new 6-digit OTP
                    landlord_verification.otp = otp  # Update OTP
                    landlord_verification.created_at = now()  # Update the created time
                    landlord_verification.save()

                    # Send OTP email
                    try:
                        send_mail(
                            subject='Verify Your Email',
                            message=f'Your OTP for email verification is: {otp}',
                            from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                            recipient_list=[],
                            fail_silently=False,  # Raise error if email fails
                        )
                    except Exception as e:
                        raise Exception(f"Failed to send email: {str(e)}")

                    return Response(
                        ResponseData.success_without_data("OTP sent successfully."),
                        status=status.HTTP_200_OK
                    )

                else:
                    # If no verification exists, create a new OTP entry
                    otp = str(random.randint(100000, 999999))  # Generate a new OTP
                    LandlordEmailVerificationModel.objects.create(
                        landlord=landlord,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )

                    # Send OTP email
                    try:
                        send_mail(
                            subject='Verify Your Email',
                            message=f'Your OTP for email verification is: {otp}',
                            from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                            recipient_list=[],
                            fail_silently=False,  # Raise error if email fails
                        )
                    except Exception as e:
                        raise Exception(f"Failed to send email: {str(e)}")

                    return Response(
                        ResponseData.success_without_data("OTP sent successfully."),
                        status=status.HTTP_200_OK
                    )

            else:
                # If the email doesn't exist, create a new landlord
                validated_data = serializer.validated_data
                validated_data['password'] = make_password(validated_data['password'])  # Hash password
                landlord = LandlordDetailsModel.objects.create(**validated_data)

                # Generate OTP for the new landlord
                otp = str(random.randint(100000, 999999))  # 6-digit OTP
                LandlordEmailVerificationModel.objects.create(
                    landlord=landlord,
                    otp=otp,
                    is_verified=False,
                    created_at=now()
                )

                # Send OTP email
                try:
                    send_mail(
                        subject='Verify Your Email',
                        message=f'Your OTP for email verification is: {otp}',
                        from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                        recipient_list=[landlord.email],
                        fail_silently=False,  # Raise error if email fails
                    )
                except Exception as e:
                    raise Exception(f"Failed to send email: {str(e)}")

                return Response(
                    ResponseData.success_without_data("Landlord signed up successfully. Please verify your email."),
                    status=status.HTTP_201_CREATED
                )
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
def get_preference_questions(request):
    """
    API to fetch all landlord questions along with their options and answers (if any).
    Expects a POST request with 'user_id' in the request data (optional for now).
    """
    # Step 1: Validate the incoming request data
    print(f'request {request.data}')
    serializer = LandlordQuestionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    user_id = serializer.validated_data.get('user_id')  # Optional for now
    bed_id = serializer.validated_data.get('bed_id')  # Optional for now

    # Step 2: Fetch the landlord based on user_id
    landlord = LandlordDetailsModel.objects.filter(id=user_id, is_active=True).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 3: Fetch all active and non-deleted landlord questions with related types and options
    questions = LandlordQuestionModel.objects.filter(
        is_active=True, 
        is_deleted=False
    ).select_related('question_type').prefetch_related('content_type')

    # Step 4: Prepare the response data
    data = []
    for question in questions:
        question_data = {
            'id': question.id,
            'question_text': question.question_text,
            'question_type': {
                'id': question.question_type.id,
                'type_name': question.question_type.type_name,
                'description': question.question_type.description
            },
            'question_options': [],
            'answers': []  # Initialize answers field
        }

        # Get the related model based on the content_type
        content_model = question.content_type.model_class() if question.content_type else None
        
        # Fetch options for the related model (like OccupationModel or any other model)
        if content_model:
            options = content_model.objects.filter(is_active=True, is_deleted=False)
            
            # Only add question to response if it has options
            if options.exists():
                question_data['question_options'] = [
                    {
                        'id': option.id,
                        'option_text': option.title  # Assuming title for options, change as needed
                    } for option in options
                ]
        
        # Fetch answers for this question by the landlord, if any
        bed_instance = LandlordRoomWiseBedModel.objects.filter(id=bed_id).first()

        if bed_instance is not None:
        # Then get its associated answers via the ManyToManyField.
            answers = bed_instance.tenant_preference_answers.filter(
                question=question,
                is_active=True,
                is_deleted=False
            ).order_by('preference')

            if answers.exists():
                for answer in answers:
                    if answer.object_id is None:
                        continue  # Skip this answer if there's no selected option
                    # For each answer, return the selected option and the preference
                    question_data['answers'].append({
                        'option_id': answer.object_id,
                        'preference': answer.preference
                    })
        
        # Add the question data to the final response
        data.append(question_data)
    
    # Step 5: Return the response
    return Response(
        ResponseData.success(data, "Landlord preferences fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def save_landlord_preferences(request):
    """
    API to save or update landlord preferences into the database.
    """
    serializer = LandlordPreferenceAnswerSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    user_id = data['user_id']
    answers = data['answers']

    # Validate landlord existence (assuming user_id is linked to a landlord)
    landlord = LandlordDetailsModel.objects.filter(id=user_id, is_active=True).first()
    if not landlord:
        return Response(
            ResponseData.error('Invalid landlord ID or landlord is not active.'),
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        ResponseData.success_without_data("Landlord preferences saved/updated successfully."),
        status=status.HTTP_201_CREATED
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

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_landlord_property_details(request):
    # 1) Validate fields
    for key, value in request.POST.items():
        print(f"{key}: {value}")

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

    property_city_instance = CityModel.objects.filter(name=property_city).first()

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
        longitude=float(longitude) if longitude else None
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
            loc = rm.get("location_in_property", "")
            n_beds = rm.get("number_of_beds")
            r_floor = rm.get("floor")
            n_windows = rm.get("number_of_windows")
            max_people = rm.get("max_people_allowed")

            if not room_type_id or not room_size:
                continue

            try:
                room_type_obj = LandlordPropertyRoomTypeModel.objects.get(id=room_type_id, is_active=True, is_deleted=False)
            except LandlordPropertyRoomTypeModel.DoesNotExist:
                continue

            room_instance = LandlordPropertyRoomDetailsModel.objects.create(
                property=property_instance,
                room_type=room_type_obj,
                room_size=room_size,
                number_of_beds=n_beds if n_beds else None,
                number_of_windows=n_windows if n_windows else None,
                max_people_allowed=max_people if max_people else None,
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
            print(f'beds_data12345 {beds_data}')
            for b_idx, bd in enumerate(beds_data):
                bed_number = bd.get("bed_number")
                is_rent_monthly = bd.get("is_rent_monthly")
                min_agreement_duration_in_months = bd.get("min_agreement_duration_in_months")
                rent_amount = bd.get("rent_amount")
                availability_start_date = bd.get("availability_start_date")
                is_available = False if availability_start_date is None else True
                print('123')
                if not rent_amount:
                    continue
                # 7.4) Bed preferences (if any)
                answers = bd.get("bed_preferences", [])
                answer_instances = []
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
                print(f'answer_instances {answer_instances}')
                # 7.4) Bed preferences (if any)
                # Could be part of bd["bed_preferences"]
                # Omitted if not needed; else handle logic similarly.

                # Create the bed_instance with conditional values
                bed_instance = LandlordRoomWiseBedModel.objects.create(
                    room=room_instance,
                    bed_number=bed_number,
                    is_available=is_available,
                    rent_amount=rent_amount,
                    availability_start_date=None if availability_start_date == "" else availability_start_date,
                    is_rent_monthly=is_rent_monthly,
                    min_agreement_duration_in_months= 0 if not is_rent_monthly else min_agreement_duration_in_months
                )


                bed_instance.tenant_preference_answers.set(answer_instances)  # Use .set() AFTER creation
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
        if os.path.exists(base_dir):
            try:
                shutil.rmtree(base_dir)
                print(f"Deleted directory: {base_dir}")
            except Exception as e:
                print(f"Error deleting directory {base_dir}: {e}")
        else:
            print(f"Directory does not exist: {base_dir}")

    return Response({"status": "success", "message": "Property details saved successfully."}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def update_landlord_property_details(request):
    try:
        # Print all POST keys and values
        try:
            for key, value in request.POST.items():
                print(f"{key}: {value}")
        except Exception as e:
            print(f"Error reading request.POST data: {str(e)}")
            return Response({'status': 'error', 'message': 'Error reading request data'}, status=status.HTTP_400_BAD_REQUEST)

        # Print files (if any are uploaded)
        try:
            for key, file in request.FILES.items():
                print(f"File - {key}: {file.name}")
        except Exception as e:
            print(f"Error reading uploaded files: {str(e)}")
            return Response({'status': 'error', 'message': 'Error reading uploaded files'}, status=status.HTTP_400_BAD_REQUEST)

        # 1) Validate required fields (including property_id)
        try:
            property_id = request.POST.get("property_id")
            if not property_id:
                return Response({"status": "error", "message": "Missing property_id."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error extracting property_id: {str(e)}")
            return Response({"status": "error", "message": "Error extracting property_id."}, status=status.HTTP_400_BAD_REQUEST)

        # 2) Get the property instance; ensure it exists and is active
        try:
            property_instance = LandlordPropertyDetailsModel.objects.get(id=property_id, is_deleted=False)
        except LandlordPropertyDetailsModel.DoesNotExist:
            return Response({"status": "error", "message": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error retrieving property instance: {str(e)}")
            return Response({"status": "error", "message": "Error retrieving property instance."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3) Update basic property fields only if provided.
        update_fields = {}
        try:
            if "propertyName" in request.POST:
                prop_name = request.POST.get("propertyName").strip()
                if property_instance.property_name != prop_name:
                    update_fields["property_name"] = prop_name

            if "propertySize" in request.POST:
                prop_size = request.POST.get("propertySize").strip()
                if property_instance.property_size != prop_size:
                    update_fields["property_size"] = prop_size

            if "propertyDescription" in request.POST:
                prop_desc = request.POST.get("propertyDescription", "").strip()
                if property_instance.property_description != prop_desc:
                    update_fields["property_description"] = prop_desc

            if "floor" in request.POST:
                floor_val = request.POST.get("floor")
                if property_instance.floor != floor_val:
                    update_fields["floor"] = floor_val

            if "number_of_rooms" in request.POST:
                number_of_rooms = request.POST.get("number_of_rooms")
                if property_instance.number_of_rooms != number_of_rooms:
                    update_fields["number_of_rooms"] = number_of_rooms

            if update_fields:
                try:
                    LandlordPropertyDetailsModel.objects.filter(id=property_id).update(**update_fields)
                except Exception as e:
                    print(f"Error updating property fields: {str(e)}")
        except Exception as e:
            print(f"Error processing basic property fields: {str(e)}")

        # 4) Update Property Amenities if provided.
        if "amenities" in request.POST:
            try:
                amenities_json = request.POST.get("amenities")
                if amenities_json:
                    try:
                        amenities_list = json.loads(amenities_json)
                    except Exception as e:
                        print(f"Error parsing amenities JSON: {str(e)}")
                        return Response({"status": "error", "message": "Invalid amenities JSON."}, status=status.HTTP_400_BAD_REQUEST)
                    print(f'amenities_list {amenities_list}')
                    if amenities_list:
                        try:
                            valid_amenities = LandlordPropertyAmenityModel.objects.filter(
                                id__in=amenities_list, is_active=True, is_deleted=False
                            )
                            if len(valid_amenities) != len(amenities_list):
                                return Response({"status": "error", "message": "One or more amenity IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)
                            property_instance.amenities.set(valid_amenities)
                        except Exception as e:
                            print(f"Error setting amenities: {str(e)}")
                            return Response({"status": "error", "message": "Error setting amenities."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                print(f"General error processing amenities: {str(e)}")

        # 6) Handle Rooms and Beds (only if "rooms" key exists)
        print(f'rooms_data {request.POST.get("rooms")}')
        if "rooms" in request.POST:
            try:
                rooms_json = request.POST.get("rooms")
                rooms_data = json.loads(rooms_json)
            except Exception as e:
                print(f"Error parsing rooms JSON: {str(e)}")
                return Response({"status": "error", "message": "Invalid rooms JSON."}, status=status.HTTP_400_BAD_REQUEST)

            for idx, rm in enumerate(rooms_data):
                try:
                    room_id = rm.get("id")
                    try:
                        room_type_id = rm.get("room_type")
                        room_size = rm.get("room_size")
                        loc = rm.get("location_in_property", "")
                        n_beds = rm.get("number_of_beds")
                        r_floor = rm.get("floor")
                        n_windows = rm.get("number_of_windows")
                        max_people = rm.get("max_people_allowed")
                    except Exception as e:
                        print(f"Error extracting new room data: {str(e)}")
                        continue

                    try:
                        room_type_obj = LandlordPropertyRoomTypeModel.objects.get(id=room_type_id, is_active=True, is_deleted=False)
                    except LandlordPropertyRoomTypeModel.DoesNotExist as e:
                        print(f"Room type {room_type_id} does not exist: {str(e)}")
                        continue
                except Exception as e:
                    print(f"Error getting room id: {str(e)}")
                    continue

                if room_id != -1:
                    try:
                        room_instance, created = LandlordPropertyRoomDetailsModel.objects.get_or_create(id=room_id)
                    except Exception as e:
                        print(f"Error getting/creating room with id {room_id}: {str(e)}")
                        continue

                    if not created:
                        update_fields = {}
                        if "room_type" in rm and room_instance.room_size != rm.get("room_type"):
                            update_fields["room_type"] = room_type_obj
                        if "room_size" in rm and room_instance.room_size != rm.get("room_size"):
                            update_fields["room_size"] = rm.get("room_size")
                        if "number_of_beds" in rm and room_instance.number_of_beds != rm.get("number_of_beds"):
                            update_fields["number_of_beds"] = rm.get("number_of_beds")
                        if "number_of_windows" in rm and room_instance.number_of_windows != rm.get("number_of_windows"):
                            update_fields["number_of_windows"] = rm.get("number_of_windows")
                        if "max_people_allowed" in rm and room_instance.max_people_allowed != rm.get("max_people_allowed"):
                            update_fields["max_people_allowed"] = rm.get("max_people_allowed")
                        if "floor" in rm and room_instance.floor != rm.get("floor"):
                            update_fields["floor"] = rm.get("floor")
                        if "location_in_property" in rm and room_instance.location_in_property != rm.get("location_in_property", ""):
                            update_fields["location_in_property"] = rm.get("location_in_property", "")
                        if update_fields:
                            print(f'update_fields_newly {update_fields}')
                            try:
                                LandlordPropertyRoomDetailsModel.objects.filter(id=room_id).update(**update_fields)
                            except Exception as e:
                                print(f"Error updating room {room_id}: {str(e)}")
                elif room_id == -1:
                    try:
                        room_instance = LandlordPropertyRoomDetailsModel.objects.create(
                            property=property_instance,
                            room_type=room_type_obj,
                            room_size=room_size,
                            number_of_beds=n_beds if n_beds else None,
                            number_of_windows=n_windows if n_windows else None,
                            max_people_allowed=max_people if max_people else None,
                            floor=r_floor if r_floor else None,
                            location_in_property=loc,
                        )
                    except Exception as e:
                        print(f"Error creating new room: {str(e)}")
                        continue

                # Handle beds (only if "beds" key is present)
                try:
                    beds_data = rm.get("beds", [])
                    print(f'beds_data_updated {beds_data}')
                except Exception as e:
                    print(f"Error getting beds data: {str(e)}")
                    continue
                # Extracting bed IDs from beds_data
                bed_ids_from_data = [bd.get("id") for bd in beds_data if bd.get("id")]
                print(f'bed_ids_from_data12 {bed_ids_from_data}')
                # Marking beds as inactive if they are NOT in the given bed_ids_from_data
                LandlordRoomWiseBedModel.objects.filter(
                    room=room_instance  # Get beds only for the current room
                ).exclude(
                    id__in=bed_ids_from_data  # Exclude beds that are present in beds_data
                ).update(is_active=False,is_deleted=True) 
                for b_idx, bd in enumerate(beds_data):
                    try:
                        bed_id = bd.get("id")
                    except Exception as e:
                        print(f"Error extracting bed id: {str(e)}")
                        continue

                    if bed_id != -1:
                        try:
                            bed_instance, created = LandlordRoomWiseBedModel.objects.get_or_create(id=bed_id)
                            print(f'Bed with id {bed_id} {"created" if created else "retrieved"}')
                        except Exception as e:
                            print(f"Error getting/creating bed with id {bed_id}: {str(e)}")
                            continue
                        print(f'bed_tenant_same_as_value {bd.get("tenant_preference_same_as")}')
                        if not created:
                            update_fields = {}
                            if "rent_amount" in bd and bed_instance.rent_amount != bd.get("rent_amount"):
                                update_fields["rent_amount"] = bd.get("rent_amount")
                            if "availability_start_date" in bd and bed_instance.availability_start_date != bd.get("availability_start_date"):
                                update_fields["availability_start_date"] = bd.get("availability_start_date")
                            if "is_rent_monthly" in bd and bed_instance.is_rent_monthly != bd.get("is_rent_monthly"):
                                update_fields["is_rent_monthly"] = bd.get("is_rent_monthly")
                            if "min_agreement_duration_in_months" in bd and bed_instance.min_agreement_duration_in_months != bd.get("min_agreement_duration_in_months"):
                                update_fields["min_agreement_duration_in_months"] = bd.get("min_agreement_duration_in_months")
                            if update_fields:
                                try:
                                    LandlordRoomWiseBedModel.objects.filter(id=bed_id).update(**update_fields)
                                    print(f"Updated bed {bed_id} with {update_fields}")
                                except Exception as e:
                                    print(f"Error updating bed {bed_id}: {str(e)}")
                        print(f"Reached bed instance: {bed_instance}")
                    elif bed_id == -1:
                        try:
                            bed_number = bd.get("bed_number")
                            is_rent_monthly = bd.get("is_rent_monthly")
                            min_agreement_duration_in_months = bd.get("min_agreement_duration_in_months")
                            rent_amount = bd.get("rent_amount")
                            availability_start_date = bd.get("availability_start_date")
                            is_available = False if availability_start_date is None else True
                            print('Creating new bed...')
                        except Exception as e:
                            print(f"Error extracting new bed data: {str(e)}")
                            continue

                        if not rent_amount:
                            continue
                        try:
                            bed_instance = LandlordRoomWiseBedModel.objects.create(
                                room=room_instance,
                                bed_number=bed_number,
                                is_available=is_available,
                                rent_amount=rent_amount,
                                availability_start_date=None if availability_start_date == "" else availability_start_date,
                                is_rent_monthly=is_rent_monthly,
                                min_agreement_duration_in_months= 0 if not is_rent_monthly else min_agreement_duration_in_months
                            )
                        except Exception as e:
                            print(f"Error creating new bed: {str(e)}")
                            continue

                    # Process bed preferences for each bed
                    try:
                        answers = bd.get("bed_preferences", [])
                        print(f'answers12345 {answers}')
                    except Exception as e:
                        print(f"Error extracting bed preferences: {str(e)}")
                        continue

                    for answer in answers:
                        try:
                            question_id = answer.get("question_id")
                            selected_answers = answer.get("priority_order", [])
                        except Exception as e:
                            print(f"Error extracting answer data: {str(e)}")
                            continue
                        try:
                            question = LandlordQuestionModel.objects.filter(id=question_id, is_active=True).first()
                            if not question:
                                print(f"Question {question_id} not found or inactive.")
                                continue
                        except Exception as e:
                            print(f"Error retrieving question {question_id}: {str(e)}")
                            continue

                        print(f'selected_answers_while_update {selected_answers}')
                        try:
                            existing_answers = bed_instance.tenant_preference_answers.filter(
                                question=question,
                                is_active=True,
                                is_deleted=False
                            ).order_by('preference')
                        except Exception as e:
                            print(f"Error retrieving existing answers for question {question_id}: {str(e)}")
                            continue

                        try:
                            if selected_answers:
                                print('Entered answer update loop')
                                new_option_ids = {ans for ans in selected_answers}
                                try:
                                    existing_answers.exclude(object_id__in=new_option_ids).delete()
                                except Exception as e:
                                    print(f"Error deleting old answers for question {question_id}: {str(e)}")
                            else:
                                try:
                                    existing_answers.delete()
                                except Exception as e:
                                    print(f"Error deleting all answers for question {question_id}: {str(e)}")
                        except Exception as e:
                            print(f"Error processing selected_answers for question {question_id}: {str(e)}")
                            continue

                        for priority, option_id in enumerate(selected_answers, start=1):
                            print(f'priority, option_id {priority}, {option_id}')
                            try:
                                try:
                                    option_content_type = ContentType.objects.get_for_model(question.question_type)
                                except Exception as e:
                                    print(f"Error retrieving content type for question {question_id}: {str(e)}")
                                    continue

                                try:
                                    answer_obj = bed_instance.tenant_preference_answers.get(
                                        question=question,
                                        content_type=option_content_type,
                                        object_id=option_id,
                                    )
                                    if answer_obj.preference != priority:
                                        answer_obj.preference = priority
                                        answer_obj.save()
                                except LandlordAnswerModel.DoesNotExist:
                                    answer_obj = LandlordAnswerModel.objects.create(
                                        landlord=property_instance.landlord,
                                        question=question,
                                        content_type=option_content_type,
                                        object_id=option_id,
                                        preference=priority,
                                    )
                                
                                if not bed_instance.tenant_preference_answers.filter(id=answer_obj.id).exists():
                                    bed_instance.tenant_preference_answers.add(answer_obj)
                            except Exception as e:
                                print(f"Error updating/creating answer for question {question_id} with option {option_id}: {str(e)}")
                    print(f"Finished processing bed {b_idx} for room {idx}")
        return Response(
            {"status": "success", "message": "Property details updated successfully."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        print(f"Unexpected error in update_landlord_property_details: {str(e)}")
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def get_property_types_and_amenities(request):
    """
    API to fetch all active landlord property types and amenities.
    Optionally accepts a 'country_code' in the request params to retrieve the currency details.
    """
    # ✅ Step 1: Fetch all active property types
    property_types = LandlordPropertyTypeModel.objects.filter(is_active=True, is_deleted=False)
    
    # ✅ Step 2: Fetch all active amenities
    amenities = LandlordPropertyAmenityModel.objects.filter(is_active=True, is_deleted=False)

    # ✅ Step 3: Prepare response data for property types and amenities
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

    # ✅ Step 4: Accept country_code from request parameters
    country_code = request.data.get("country_code", "").strip()
    if country_code:
        country = CountryModel.objects.get(iso2__iexact=country_code)

    # ✅ Step 5: Return the structured response
    return Response(
        ResponseData.success(
            {
                "property_types": property_types_data,
                "amenities": amenities_data,
                "currency_name": country.currency_name,
                "currency_symbol": country.currency_symbol
            },
            "Property types and amenities fetched successfully."
        ),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def get_landlord_properties(request):
    """
    API to fetch all properties for a landlord (basic details).
    Expects POST request with {'landlord_id': int}
    """
    serializer = PropertyListRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    landlord_id = serializer.validated_data['landlord_id']

    properties = LandlordPropertyDetailsModel.objects.filter(
        landlord_id=landlord_id,
        is_active=True,
        is_deleted=False
    ).prefetch_related(
        Prefetch(
            'property_media',
            queryset=LandlordPropertyMediaModel.objects.filter(is_active=True, is_deleted=False)
        ),
        'property_type'
    )
    # ✅ Construct response data with file paths instead of objects
    property_list = []
    for prop in properties:
        property_list.append({
            "id": prop.id,
            "property_name": prop.property_name,
            "property_address": prop.property_address,
            "property_size": prop.property_size,
            "property_type_name": prop.property_type.type_name if prop.property_type else None,
            "number_of_rooms": prop.number_of_rooms,
            "property_media": [media.file.url for media in prop.property_media.all()],  # ✅ File paths
            "bed_tabs_title" : build_all_tabs(prop.id)
        })

    return Response(
        ResponseData.success(property_list, "Properties fetched successfully"),
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
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



@api_view(["POST"])
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

    if room_id != -1:
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
    elif bed_id != -1:
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