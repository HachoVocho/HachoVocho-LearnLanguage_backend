from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from landlord.models import LandlordDetailsModel, LandlordPropertyDetailsModel, LandlordRoomWiseBedModel
from .models import LandlordAvailabilityModel, LandlordAvailabilitySlotModel
from .serializers import AddLandlordAvailabilitySerializer, GetLandlordAvailabilityByBedSerializer, GetLandlordAvailabilitySerializer
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated  # Importing ResponseData class
import datetime
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_landlord_availability(request):
    """
    API to add landlord availability for a specific property on a given date.
    Divides the given time period into equal slots based on max_meetings.
    """
    print(f'request.data {request.data}')
    serializer = AddLandlordAvailabilitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id = serializer.validated_data["landlord_id"]
    property_id = serializer.validated_data["property_id"]
    date = serializer.validated_data["date"]
    time_slots = serializer.validated_data["time_slots"]

    # Validate landlord and property
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )

    property_instance = LandlordPropertyDetailsModel.objects.filter(
        id=property_id, landlord=landlord, is_active=True, is_deleted=False
    ).first()
    if not property_instance:
        return Response(
            ResponseData.error("Invalid property ID or property does not belong to this landlord."),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create or update availability
    availability, created = LandlordAvailabilityModel.objects.update_or_create(
        landlord=landlord,
        property=property_instance,
        date=date,
        defaults={"is_active": True, "is_deleted": False, "updated_at": now()},
    )

    # Loop over each provided time slot data from the request
    print(f'time_slots {time_slots}')
    for slot in time_slots:
        start_time_str = slot.get("start_time")
        end_time_str = slot.get("end_time")
        # Convert max_meetings to int, defaulting to 1 if conversion fails.
        try:
            max_meetings = int(slot.get("max_meetings", 1))
        except ValueError:
            max_meetings = 1
        print(f'max_meetings {max_meetings}')
        if not start_time_str or not end_time_str:
            continue

        try:
            # Convert start and end times from strings (expected format "HH:MM") to time objects
            start_time_obj = datetime.datetime.strptime(start_time_str, "%H:%M").time()
            end_time_obj = datetime.datetime.strptime(end_time_str, "%H:%M").time()

            # Create dummy datetime objects (using a fixed date) to calculate the duration
            dummy_date = datetime.date(1900, 1, 1)
            start_dt = datetime.datetime.combine(dummy_date, start_time_obj)
            end_dt = datetime.datetime.combine(dummy_date, end_time_obj)

            # Ensure end_dt is after start_dt; if not, skip this slot
            if end_dt <= start_dt:
                continue
            print(f'start_dt {start_dt}')
            total_duration = (end_dt - start_dt).total_seconds()  # total duration in seconds
            slot_duration = total_duration / max_meetings  # duration for each slot in seconds
            print(f'slot_duration {slot_duration}')
            # Create individual slots by dividing the time range
            for i in range(max_meetings):
                slot_start = start_dt + datetime.timedelta(seconds=i * slot_duration)
                slot_end = start_dt + datetime.timedelta(seconds=(i + 1) * slot_duration)

                LandlordAvailabilitySlotModel.objects.create(
                    availability=availability,
                    start_time=slot_start.time(),
                    end_time=slot_end.time(),
                )
        except Exception as e:
            # Log the error or handle it as needed
            print(f"Error processing slot: {e}")
            continue

    return Response(
        ResponseData.success_without_data("Landlord availability added successfully."),
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_availability_by_month(request):
    """
    API to fetch all landlord availabilities for a specific property,
    optionally filtered by a given month.
    """
    serializer = GetLandlordAvailabilitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    ld_id   = serializer.validated_data["landlord_id"]
    prop_id = serializer.validated_data["property_id"]
    month   = serializer.validated_data.get("month", None)

    # Base queryset
    qs = LandlordAvailabilityModel.objects.filter(
        landlord_id=ld_id,
        property_id=prop_id,
        is_active=True,
        is_deleted=False
    )
    # Only filter by month if provided
    if month is not None:
        qs = qs.filter(date__month=month)

    if not qs.exists():
        return Response(
            ResponseData.success_without_data(
                "No availability found for this property" +
                (f" in month {month}." if month else ".")
            ),
            status=status.HTTP_200_OK
        )

    all_availabilities = []
    for availability in qs.order_by("date"):
        slots = LandlordAvailabilitySlotModel.objects.filter(
            availability=availability,
            is_active=True,
            is_deleted=False
        ).order_by("start_time")

        slots_data = [
            {
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time":   slot.end_time.strftime("%H:%M"),
                "date":       slot.availability.date.strftime("%Y-%m-%d"),
            }
            for slot in slots
        ]

        if slots_data:
            all_availabilities.append({
                "date":       availability.date.strftime("%Y-%m-%d"),
                "time_slots": slots_data,
                "landlord_id" : ld_id,
                "property_id" : prop_id,
            })
        print(f'all_availabilities {all_availabilities}')

    return Response(
        ResponseData.success(all_availabilities, "Availabilities fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_availability_by_property(request):
    """
    API to fetch all future availabilities for the property
    to which the given bed belongs.
    """
    print("\n=== STARTING get_landlord_availability_by_property ===")
    print(f"Initial request data: {request.data}")
    
    data = request.data.copy()
    
    # If they only sent bed_id, look up the property_id & landlord_id
    bed_id = data.get("bed_id")
    if bed_id and (not data.get("property_id") or not data.get("landlord_id")):
        print(f"Only bed_id provided ({bed_id}), looking up property and landlord...")
        
        try:
            bed = LandlordRoomWiseBedModel.objects.get(
                pk=bed_id,
                is_deleted=False,
                is_active=True,
            )
            print(f"Found bed: {bed.id} (Room: {bed.room.id if bed.room else None})")
            
            # navigate up: bed → room → property → landlord
            room = bed.room
            prop = room.property
            landlord = prop.landlord
            
            data["property_id"] = prop.id
            data["landlord_id"] = landlord.id
            
            print(f"Derived property_id: {prop.id}, landlord_id: {landlord.id}")
            
        except LandlordRoomWiseBedModel.DoesNotExist:
            print(f"Error: Bed with id {bed_id} not found")
            return Response(
                ResponseData.error({"bed_id": "Invalid bed_id"}),
                status=status.HTTP_400_BAD_REQUEST
            )

    print(f"Final data for serializer: {data}")
    
    # now run through your existing serializer & logic
    serializer = GetLandlordAvailabilityByBedSerializer(data=data)
    if not serializer.is_valid():
        print(f"Serializer errors: {serializer.errors}")
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    property_id = serializer.validated_data["property_id"]
    landlord_id = serializer.validated_data["landlord_id"]
    
    print(f"Querying availabilities for landlord_id: {landlord_id}, property_id: {property_id}")

    # all availabilities for this landlord & property
    qs = LandlordAvailabilityModel.objects.filter(
        landlord_id=landlord_id,
        property_id=property_id,
        is_active=True,
        is_deleted=False
    ).order_by("date")

    print(f"Found {qs.count()} availability days")
    
    if not qs.exists():
        print("No availability records found")
        return Response(
            ResponseData.success_without_data(
                "No availability found for bed's property."
            ),
            status=status.HTTP_200_OK
        )

    result = []
    for availability in qs:
        print(f"\nProcessing availability for date: {availability.date}")
        
        slots = LandlordAvailabilitySlotModel.objects.filter(
            availability=availability,
            is_active=True,
            is_deleted=False
        ).order_by("start_time")

        print(f"Found {slots.count()} slots for this date")
        
        slots_data = [
            {
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time":   slot.end_time.strftime("%H:%M"),
                "slot_id":    slot.id,
            }
            for slot in slots
        ]
        
        if slots_data:
            print(f"Adding {len(slots_data)} slots to result")
            result.append({
                "date":       availability.date.strftime("%Y-%m-%d"),
                "time_slots": slots_data,
            })
        else:
            print("No active slots found for this date")

    print(f"\nFinal result contains {len(result)} days with availability")
    print("=== END get_landlord_availability_by_property ===")
    
    return Response(
        ResponseData.success(result, "Availabilities fetched successfully."),
        status=status.HTTP_200_OK
    )