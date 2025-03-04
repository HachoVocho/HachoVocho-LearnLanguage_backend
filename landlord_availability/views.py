from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from landlord.models import LandlordDetailsModel, LandlordPropertyDetailsModel
from .models import LandlordAvailabilityModel, LandlordAvailabilitySlotModel
from .serializers import AddLandlordAvailabilitySerializer, GetLandlordAvailabilitySerializer
from response import Response as ResponseData  # Importing ResponseData class
import datetime

@api_view(["POST"])
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
def get_landlord_availability_by_month(request):
    """
    API to fetch all landlord availabilities for a specific property and month.
    """
    print(f'request.data {request.data}')
    serializer = GetLandlordAvailabilitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id = serializer.validated_data["landlord_id"]
    property_id = serializer.validated_data["property_id"]
    month = serializer.validated_data["month"]  # Extract month from request

    # Filter availabilities for the specified month
    availabilities = LandlordAvailabilityModel.objects.filter(
        landlord_id=landlord_id,
        property_id=property_id,
        date__month=month,  # Filter by month
        is_active=True,
        is_deleted=False
    )

    if not availabilities.exists():
        return Response(
            ResponseData.success_without_data("No availability found for this property and month."),
            status=status.HTTP_200_OK
        )

    all_availabilities = []
    
    for availability in availabilities:
        slots = LandlordAvailabilitySlotModel.objects.filter(
            availability=availability, is_active=True, is_deleted=False
        )

        slots_data = [
            {
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "date": availability.date.strftime("%Y-%m-%d")
            }
            for slot in slots
        ]

        all_availabilities.append({
            "landlord_id": landlord_id,
            "property_id": property_id,
            "time_slots": slots_data,
        })

    return Response(
        ResponseData.success(all_availabilities, "All landlord availabilities fetched successfully."),
        status=status.HTTP_200_OK
    )

