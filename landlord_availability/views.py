import datetime
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django.utils.timezone import now

from landlord.models import LandlordDetailsModel, LandlordPropertyDetailsModel
from .models import LandlordAvailabilityModel, LandlordAvailabilitySlotModel
from .serializers import AddLandlordAvailabilitySerializer, DeleteLandlordAvailabilitySlotSerializer, GetLandlordAvailabilityDatesSerializer, GetLandlordAvailabilitySlotsSerializer
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_landlord_availability(request):
    """
    API to add landlord availability for a specific property on one date
    or over a date-range (inclusive). Divides each given time period into
    equal slots based on max_meetings.
    """
    print(f'request.data {request.data}')
    serializer = AddLandlordAvailabilitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id   = serializer.validated_data["landlord_id"]
    property_id   = serializer.validated_data["property_id"]
    single_date   = serializer.validated_data.get("date")
    start_date    = serializer.validated_data.get("start_date")
    end_date      = serializer.validated_data.get("end_date")
    time_slots    = serializer.validated_data["time_slots"]

    # Build the list of target dates
    if start_date and end_date:
        dates = []
        cur = start_date
        while cur <= end_date:
            dates.append(cur)
            cur += datetime.timedelta(days=1)
    else:
        dates = [single_date]

    # Validate landlord and property once
    landlord = LandlordDetailsModel.objects.filter(
        id=landlord_id, is_active=True, is_deleted=False
    ).first()
    if not landlord:
        return Response(
            ResponseData.error("Invalid landlord ID or landlord is not active."),
            status=status.HTTP_400_BAD_REQUEST
        )

    property_instance = LandlordPropertyDetailsModel.objects.filter(
        id=property_id,
        landlord=landlord,
        is_active=True,
        is_deleted=False
    ).first()
    if not property_instance:
        return Response(
            ResponseData.error("Invalid property ID or property does not belong to this landlord."),
            status=status.HTTP_400_BAD_REQUEST
        )

    # For each date in the range (or the single date), upsert availability + slots
    for this_date in dates:
        availability, created = LandlordAvailabilityModel.objects.update_or_create(
            landlord=landlord,
            property=property_instance,
            date=this_date,
            defaults={"is_active": True, "is_deleted": False, "updated_at": now()},
        )

        print(f'Processing {len(time_slots)} time_slots for date {this_date}')
        for slot in time_slots:
            start_time_str = slot.get("start_time")
            end_time_str   = slot.get("end_time")
            try:
                max_meetings = int(slot.get("max_meetings", 1))
            except (ValueError, TypeError):
                max_meetings = 1

            if not start_time_str or not end_time_str:
                continue

            try:
                start_time_obj = datetime.datetime.strptime(start_time_str, "%H:%M").time()
                end_time_obj   = datetime.datetime.strptime(end_time_str,   "%H:%M").time()

                # Dummy date for duration calc
                dummy_date = datetime.date(1900, 1, 1)
                start_dt = datetime.datetime.combine(dummy_date, start_time_obj)
                end_dt   = datetime.datetime.combine(dummy_date, end_time_obj)
                if end_dt <= start_dt:
                    continue

                total_seconds = (end_dt - start_dt).total_seconds()
                slot_seconds  = total_seconds / max_meetings

                for i in range(max_meetings):
                    slot_start = start_dt + datetime.timedelta(seconds=i * slot_seconds)
                    slot_end   = start_dt + datetime.timedelta(seconds=(i + 1) * slot_seconds)

                    LandlordAvailabilitySlotModel.objects.create(
                        availability=availability,
                        start_time = slot_start.time(),
                        end_time   = slot_end.time(),
                    )
            except Exception as e:
                print(f"Error processing slot on {this_date}: {e}")
                continue

    return Response(
        ResponseData.success_without_data("Landlord availability added successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_availability_dates(request):
    """
    Returns only the dates on which this landlord/property has availability,
    along with a slot_count for each date.
    Optional 'month' to filter by calendar‐month.
    """
    serializer = GetLandlordAvailabilityDatesSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    ld_id   = serializer.validated_data["landlord_id"]
    prop_id = serializer.validated_data["property_id"]
    month   = serializer.validated_data.get("month", None)

    # Base queryset for availability dates
    qs = LandlordAvailabilityModel.objects.filter(
        landlord_id=ld_id,
        property_id=prop_id,
        is_active=True,
        is_deleted=False
    )
    if month is not None:
        qs = qs.filter(date__month=month)

    # If no availabilities, return empty
    if not qs.exists():
        return Response(
            ResponseData.success_without_data("No availability dates found."),
            status=status.HTTP_200_OK
        )

    # Build list of { date, slot_count }
    result = []
    for avail in qs.order_by("date"):
        count = LandlordAvailabilitySlotModel.objects.filter(
            availability=avail,
            is_active=True,
            is_deleted=False
        ).count()
        result.append({
            "date":       avail.date.strftime("%Y-%m-%d"),
            "slot_count": count
        })

    return Response(
        ResponseData.success(result, "Availability dates fetched."),
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_availability_slots(request):
    """
    Given landlord_id and property_id, and optionally date,
    return that day’s slots (if date provided) or every available date’s slots.
    """
    serializer = GetLandlordAvailabilitySlotsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    ld_id    = serializer.validated_data["landlord_id"]
    prop_id  = serializer.validated_data["property_id"]
    date_obj = serializer.validated_data.get("date")

    # Base availability queryset for this landlord/property
    avail_qs = LandlordAvailabilityModel.objects.filter(
        landlord_id=ld_id,
        property_id=prop_id,
        is_active=True,
        is_deleted=False
    )

    # If a specific date was requested, filter it
    if date_obj:
        avail_qs = avail_qs.filter(date=date_obj)

    # no records → return empty list under data
    if not avail_qs.exists():
        return Response(
            ResponseData.success([], "No availability found."),
            status=status.HTTP_200_OK
        )

    result = []
    for avail in avail_qs.order_by("date"):
        slots_qs = LandlordAvailabilitySlotModel.objects.filter(
            availability=avail,
            is_active=True,
            is_deleted=False
        ).order_by("start_time")

        slots_data = [
            {
                "slot_id":    slot.id,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time":   slot.end_time.strftime("%H:%M"),
            }
            for slot in slots_qs
        ]

        result.append({
            "date":       avail.date.strftime("%Y-%m-%d"),
            "time_slots": slots_data
        })

    return Response(
        ResponseData.success(result, "Time slots fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_landlord_availability_slot(request):
    """
    Soft-delete one or more time slots.
    You can pass either:
      { "slot_id": 123 }
    or
      { "slot_ids": [123, 124, 125] }
    """
    serializer = DeleteLandlordAvailabilitySlotSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(ResponseData.error(serializer.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    # collect IDs
    ids = []
    if data.get("slot_id"):
        ids = [data["slot_id"]]
    else:
        ids = data["slot_ids"]

    # fetch all matching active slots
    qs = LandlordAvailabilitySlotModel.objects.filter(
        id__in=ids,
        is_active=True,
        is_deleted=False
    )
    if not qs.exists():
        return Response(ResponseData.error("No matching active slots found."),
                        status=status.HTTP_404_NOT_FOUND)

    # mark them soft-deleted
    updated = qs.update(is_active=False, is_deleted=True)

    return Response(
        ResponseData.success_without_data(
            f"{updated} slot{'s' if updated>1 else ''} deleted successfully."
        ),
        status=status.HTTP_200_OK
    )
    
