from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import GetAppointmentsSerializer
from .models import AppointmentBookingModel
from response import Response as ResponseData

@api_view(["POST"])
def get_appointments(request):
    """
    API to fetch all appointments for a specific tenant.
    """
    print(f'request.data {request.data}')
    serializer = GetAppointmentsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"status": "error", "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Extract validated data
    tenant_id = serializer.validated_data.get("tenant_id")

    # Filter appointments for the specific tenant
    appointments = AppointmentBookingModel.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False
    )

    if not appointments.exists():
        return Response(ResponseData.success_without_data("No appointments found for this tenant."), status=status.HTTP_200_OK)

    all_appointments = []
    
    for appointment in appointments:
        # Fetch tenant details

        # Fetch landlord details
        landlord = appointment.landlord
        landlord_data = {
            "id": landlord.id,
            "first_name": landlord.first_name,
            "last_name": landlord.last_name,
        }

        # Fetch bed details
        bed = appointment.bed
        bed_data = {
            "id": bed.id,
            "bed_number": bed.bed_number,
            "room_type": bed.room.room_type.type_name,  # Assuming room_type is a field in the Room model
        }

        # Fetch time slot details
        time_slot = appointment.time_slot
        slot_data = {
            "start_time": time_slot.start_time.strftime("%H:%M"),
            "end_time": time_slot.end_time.strftime("%H:%M"),
        }

        all_appointments.append({
            "appointment_id": appointment.id,
            "landlord": landlord_data,
            "bed": bed_data,
            "time_slot": slot_data,
            "status": appointment.status,
            "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return Response(ResponseData.success(all_appointments,"Appointments fetched successfully."), status=status.HTTP_200_OK)
