from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from landlord.models import LandlordDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel
from tenant.models import TenantDetailsModel
from .serializers import BookAppointmentSerializer, GetAppointmentsSerializer
from .models import AppointmentBookingModel
from response import Response as ResponseData
from collections import defaultdict
from django.utils.timezone import now

@api_view(["POST"])
def get_tenant_appointments(request):
    """
    API to fetch all appointments for a specific tenant, optionally filtering by status.
    Expected request payload:
    {
        "tenant_id": int,
        "status": "pending"|"confirmed"|"cancelled"|"completed"   # optional
    }
    ResponseData.success([...], "Appointments fetched successfully")
    """
    print(f'request.data {request.data}')
    serializer = GetAppointmentsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant_id = serializer.validated_data["tenant_id"]
    status_filter = serializer.validated_data.get("status")

    # Base queryset: active, not deleted appointments for this tenant
    qs = AppointmentBookingModel.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False,
    )

    if status_filter != '':
        # If status provided, only those
        qs = qs.filter(status=status_filter)

    if not qs.exists():
        return Response(
            ResponseData.success_without_data("No appointments found for this tenant."),
            status=status.HTTP_200_OK
        )

    all_appointments = []
    for idx, appointment in enumerate(qs.select_related('landlord', 'bed__room__property', 'time_slot'), start=1):
        landlord = appointment.landlord
        landlord_data = {
            "id": landlord.id,
            "first_name": landlord.first_name,
            "last_name": landlord.last_name,
        }

        bed = appointment.bed
        room = bed.room
        bed_data = {
            "id": bed.id,
            "bed_number": bed.bed_number,
            "room_number": idx,
            "room_type": room.room_type.type_name if room.room_type else None,
        }

        slot = appointment.time_slot
        time_slot = {
            "slot_id": slot.id,
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "date": slot.availability.date.strftime("%Y-%m-%d"),
        }

        all_appointments.append({
            "appointment_id": appointment.id,
            "landlord": landlord_data,
            "bed": bed_data,
            "time_slot": time_slot,
            "status": appointment.status,
            "initiated_by": appointment.initiated_by,
            "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": room.property.property_name if room.property else None,
            "property_id": room.property.id if room.property else None,
        })

    return Response(
        ResponseData.success(all_appointments, "Appointments fetched successfully."),
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
def get_landlord_appointments(request):
    """
    API to fetch all appointments for a specific landlord AND property.
    Expected request payload:
    {
        "landlord_id": int,
        "property_id": int
    }
    """
    serializer = GetAppointmentsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"status": "error", "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    landlord_id = serializer.validated_data["landlord_id"]
    property_id = serializer.validated_data.get("property_id")  # <-- now reading it

    # Filter appointments for this landlord *and* this property
    appointments = AppointmentBookingModel.objects.filter(
        landlord_id=landlord_id,
        bed__room__property__id=property_id,
        is_active=True,
        is_deleted=False,
    )

    if not appointments.exists():
        return Response(
            ResponseData.success_without_data("No appointments found."),
            status=status.HTTP_200_OK
        )

    all_appointments = []
    for idx, appointment in enumerate(appointments, start=1):
        tenant = appointment.tenant
        bed = appointment.bed
        room = bed.room
        time_slot = appointment.time_slot

        all_appointments.append({
            "appointment_id": appointment.id,
            "landlord": {
                "id": appointment.landlord.id,
                "first_name": appointment.landlord.first_name,
                "last_name": appointment.landlord.last_name,
            },
            "tenant": {
                "id": tenant.id,
                "first_name": tenant.first_name,
                "last_name": tenant.last_name,
            },
            "bed": {
                "id": bed.id,
                "bed_number": bed.bed_number,
                "room_number": idx,
                "room_type": room.room_type.type_name if room.room_type else None,
            },
            "time_slot": {
                "start_time": time_slot.start_time.strftime("%H:%M"),
                "end_time": time_slot.end_time.strftime("%H:%M"),
                "date": time_slot.availability.date.strftime("%Y-%m-%d"),
                "slot_id": time_slot.id,
            },
            "status": appointment.status,
            "initiated_by": appointment.initiated_by,
            "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": room.property.property_name,
        })

    return Response(
        ResponseData.success(all_appointments, "Appointments fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def book_appointment(request):
    """
    API to allow a landlord to book an appointment slot for a tenant.
    Expected request payload:
    {
        "tenant_id":   int,
        "landlord_id": int,
        "bed_id":      int,
        "slot_id":     int
    }
    On success returns only a message (no data).
    """
    serializer = BookAppointmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant_id   = serializer.validated_data["tenant_id"]
    landlord_id = serializer.validated_data["landlord_id"]
    bed_id      = serializer.validated_data["bed_id"]
    slot_id     = serializer.validated_data["slot_id"]

    # Validate foreign keys
    try:
        tenant   = TenantDetailsModel.objects.get(pk=tenant_id,   is_active=True, is_deleted=False)
        landlord = LandlordDetailsModel.objects.get(pk=landlord_id, is_active=True, is_deleted=False)
        bed      = LandlordRoomWiseBedModel.objects.get(pk=bed_id, is_active=True, is_deleted=False)
        slot     = LandlordAvailabilitySlotModel.objects.get(pk=slot_id, is_active=True, is_deleted=False)
    except (TenantDetailsModel.DoesNotExist,
            LandlordDetailsModel.DoesNotExist,
            LandlordRoomWiseBedModel.DoesNotExist,
            LandlordAvailabilitySlotModel.DoesNotExist) as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Prevent duplicate booking
    if AppointmentBookingModel.objects.filter(
        tenant=tenant,
        landlord=landlord,
        bed=bed,
        time_slot=slot,
        is_active=True,
        is_deleted=False
    ).exists():
        return Response(
            ResponseData.error("This slot is already booked."),
            status=status.HTTP_409_CONFLICT
        )

    # Create new booking
    AppointmentBookingModel.objects.create(
        tenant=tenant,
        landlord=landlord,
        bed=bed,
        time_slot=slot,
        status="pending",
        initiated_by="landlord"
    )

    # Only return a success‐without‐data message
    return Response(
        ResponseData.success_without_data("Appointment booked successfully."),
        status=status.HTTP_201_CREATED
    )