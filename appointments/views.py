from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import GetAppointmentsSerializer
from .models import AppointmentBookingModel
from response import Response as ResponseData

@api_view(["POST"])
def get_tenant_appointments(request):
    """
    API to fetch all appointments for a specific tenant.
    Expected request payload:
    {
        "tenant_id": int
    }
    ResponseData.success({
        "appointment_id": ...,
        "landlord": {
            "id": ...,
            "first_name": ...,
            "last_name": ...
        },
        "bed": {
            "id": ...,
            "bed_number": ...,
            "room_number": ...,   # Enumerated room number (index)
            "room_type": ...
        },
        "time_slot": {
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "date": "YYYY-MM-DD"
        },
        "status": ...,
        "created_at": "YYYY-MM-DD HH:MM:SS",
        "property_name": ...
    }, "Appointments fetched successfully")
    """
    print(f'request.data {request.data}')
    serializer = GetAppointmentsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant_id = serializer.validated_data.get("tenant_id")

    # Filter appointments for the specific tenant and exclude pending ones.
    appointments = AppointmentBookingModel.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False
    ).exclude(status="pending")

    if not appointments.exists():
        return Response(
            ResponseData.success_without_data("No appointments found for this tenant."),
            status=status.HTTP_200_OK
        )

    all_appointments = []
    
    for idx, appointment in enumerate(appointments, start=1):
        # Fetch landlord details
        landlord = appointment.landlord
        landlord_data = {
            "id": landlord.id,
            "first_name": landlord.first_name,
            "last_name": landlord.last_name,
        }

        # Fetch bed details
        bed = appointment.bed
        room = bed.room  # Assuming room is a LandlordPropertyRoomDetailsModel instance
        bed_data = {
            "id": bed.id,
            "bed_number": bed.bed_number,
            "room_number": idx,  # Using the index as the room number
            "room_type": room.room_type.type_name if room.room_type else None,
        }

        # Fetch time slot details
        time_slot = appointment.time_slot
        slot_data = {
            "start_time": time_slot.start_time.strftime("%H:%M"),
            "end_time": time_slot.end_time.strftime("%H:%M"),
            "date": str(time_slot.created_at).split(' ')[0],
        }

        # Fetch property name from the room
        property_name = room.property.property_name if room.property else None

        all_appointments.append({
            "appointment_id": appointment.id,
            "landlord": landlord_data,
            "bed": bed_data,
            "time_slot": slot_data,
            "status": appointment.status,
            "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": property_name,
        })

    return Response(
        ResponseData.success(all_appointments, "Appointments fetched successfully."),
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def get_landlord_appointments(request):
    """
    API to fetch all appointments for a specific landlord.
    """
    print(f'request.data {request.data}')
    serializer = GetAppointmentsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"status": "error", "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Extract validated data
    landlord_id = serializer.validated_data.get("landlord_id")

    # Filter appointments for the specific landlord
    appointments = AppointmentBookingModel.objects.filter(
        landlord_id=landlord_id,
        is_active=True,
        is_deleted=False,
    ).exclude(status="pending")

    if not appointments.exists():
        return Response(ResponseData.success_without_data("No appointments found for this landlord."), status=status.HTTP_200_OK)

    all_appointments = []
        
    for idx, appointment in enumerate(appointments, start=1):
        # Fetch tenant details
        tenant = appointment.tenant
        tenant_data = {
            "id": tenant.id,
            "first_name": tenant.first_name,
            "last_name": tenant.last_name,
        }

        # Fetch bed details
        bed = appointment.bed
        room = bed.room  # This is a LandlordPropertyRoomDetailsModel instance
        bed_data = {
            "id": bed.id,
            "bed_number": bed.bed_number,
            # Instead of room.id, use the index (idx) + 1
            "room_number": idx,
            "room_type": room.room_type.type_name,
        }

        # Fetch time slot details
        time_slot = appointment.time_slot

        slot_data = {
            "start_time": time_slot.start_time.strftime("%H:%M"),
            "end_time": time_slot.end_time.strftime("%H:%M"),
            "date": str(time_slot.created_at).split(' ')[0]
        }

        # Fetch property details from the room
        property_name = room.property.property_name

        all_appointments.append({
            "appointment_id": appointment.id,
            "tenant": tenant_data,
            "bed": bed_data,
            "time_slot": slot_data,
            "status": appointment.status,
            "initiated_by": appointment.initiated_by,  # Include who initiated the appointment
            "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": property_name,  # Added property name
        })


    return Response(ResponseData.success(all_appointments, "Appointments fetched successfully."), status=status.HTTP_200_OK)