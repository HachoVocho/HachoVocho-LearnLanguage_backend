# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now

from .models import AppointmentBookingModel
from .serializers import BookAppointmentSerializer, GetAppointmentsSerializer
from landlord.models import LandlordDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel
from tenant.models import TenantDetailsModel
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

# 1) Tenant’s view — request.user is the tenant
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_tenant_appointments(request):
    """
    Fetch all appointments for the authenticated tenant, optionally filtering by status.
    Body: {"status": "pending"|"confirmed"|"cancelled"|"completed"}  # optional
    """
    status_filter = request.data.get("status", "")

    qs = AppointmentBookingModel.objects.filter(
        tenant=request.user,
        is_active=True,
        is_deleted=False,
    )
    if status_filter:
        qs = qs.filter(status=status_filter)

    if not qs.exists():
        return Response(
            ResponseData.success_without_data("No appointments found for this tenant."),
            status=status.HTTP_200_OK
        )

    all_appointments = []
    for idx, appt in enumerate(qs.select_related('landlord', 'bed__room__property', 'time_slot'), start=1):
        bed = appt.bed
        room = bed.room
        slot = appt.time_slot

        all_appointments.append({
            "appointment_id": appt.id,
            "landlord": {
                "id": appt.landlord.id,
                "first_name": appt.landlord.first_name,
                "last_name": appt.landlord.last_name,
            },
            "bed": {
                "id": bed.id,
                "bed_number": bed.bed_number,
                "room_number": idx,
                "room_type": room.room_type.type_name if room.room_type else None,
            },
            "time_slot": {
                "slot_id": slot.id,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "date": slot.availability.date.strftime("%Y-%m-%d"),
            },
            "status": appt.status,
            "initiated_by": appt.initiated_by,
            "created_at": appt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": room.property.property_name if room.property else None,
            "property_id": room.property.id if room.property else None,
        })

    return Response(
        ResponseData.success(all_appointments, "Appointments fetched successfully."),
        status=status.HTTP_200_OK
    )


# 2) Landlord’s view — request.user is the landlord
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_landlord_appointments(request):
    """
    Fetch all appointments for the authenticated landlord, optionally filtering by property.
    Body: {"property_id": int}  # optional
    """
    property_id = request.data.get("property_id", None)

    qs = AppointmentBookingModel.objects.filter(
        landlord=request.user,
        is_active=True,
        is_deleted=False,
    )
    if property_id is not None:
        qs = qs.filter(bed__room__property__id=property_id)

    if not qs.exists():
        return Response(
            ResponseData.success_without_data("No appointments found."),
            status=status.HTTP_200_OK
        )

    all_appointments = []
    for idx, appt in enumerate(qs.select_related('tenant', 'bed__room__property', 'time_slot'), start=1):
        bed = appt.bed
        room = bed.room
        slot = appt.time_slot

        all_appointments.append({
            "appointment_id": appt.id,
            "landlord": {
                "id": appt.landlord.id,
                "first_name": appt.landlord.first_name,
                "last_name": appt.landlord.last_name,
            },
            "tenant": {
                "id": appt.tenant.id,
                "first_name": appt.tenant.first_name,
                "last_name": appt.tenant.last_name,
            },
            "bed": {
                "id": bed.id,
                "bed_number": bed.bed_number,
                "room_number": idx,
                "room_type": room.room_type.type_name if room.room_type else None,
            },
            "time_slot": {
                "slot_id": slot.id,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "date": slot.availability.date.strftime("%Y-%m-%d"),
            },
            "status": appt.status,
            "initiated_by": appt.initiated_by,
            "created_at": appt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "property_name": room.property.property_name if room.property else None,
        })

    return Response(
        ResponseData.success(all_appointments, "Appointments fetched successfully."),
        status=status.HTTP_200_OK
    )


# 3) Booking view — landlord books for a tenant
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def book_appointment(request):
    """
    Authenticated landlord books an available slot for a tenant.
    Body: {
        "tenant_id": int,
        "bed_id": int,
        "slot_id": int
    }
    """
    serializer = BookAppointmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant = TenantDetailsModel.objects.get(
        pk=serializer.validated_data["tenant_id"],
        is_active=True, is_deleted=False
    )
    bed = LandlordRoomWiseBedModel.objects.get(
        pk=serializer.validated_data["bed_id"],
        is_active=True, is_deleted=False
    )
    slot = LandlordAvailabilitySlotModel.objects.get(
        pk=serializer.validated_data["slot_id"],
        is_active=True, is_deleted=False
    )

    # Prevent duplicate booking
    if AppointmentBookingModel.objects.filter(
        tenant=tenant,
        landlord=bed.room.property.landlord,
        bed=bed,
        time_slot=slot,
        status='confirmed',
        is_active=True,
        is_deleted=False
    ).exists():
        return Response(
            ResponseData.error("This slot is already booked."),
            status=status.HTTP_409_CONFLICT
        )
    landlord = bed.room.property.landlord
    appt = AppointmentBookingModel.objects.create(
        tenant=tenant,
        landlord=bed.room.property.landlord,
        bed=bed,
        time_slot=slot,
        status="pending",
        initiated_by="landlord"
    )

    # send websocket notifications…
    notification = {
        "type": "appointment_created_notification_by_tenant",
        "message": {
            "appointmentId": appt.id,
            "tenantId":   tenant.id,
            "landlordId": landlord.id,
            "bedId":      bed.id,
            "roomId":     bed.room.id,
            "slotId":     slot.id,
            "status":     appt.status,
        }
    }
    channel_layer = get_channel_layer()
    groups = [
        f"landlord_{request.user.id}",
        f"landlord_{landlord.id}_property_{bed.room.property.id}",
        f"property_{bed.room.property.id}_bed_{bed.id}",
        f"property_{bed.room.property.id}"
    ]
    for grp in groups:
        async_to_sync(channel_layer.group_send)(grp, notification)

    slot = appt.time_slot
    bed = appt.bed
    room = bed.room
    prop = room.property if room else None

    result = {
        "appointmentId":   appt.id,
        "landlordId":      landlord.id,
        "tenantId":        tenant.id,
        "bedId":           bed.id,
        "bedNumber":       bed.bed_number,
        "roomId":          room.id if room else None,
        "roomNumber":      room.room_name if room else None,
        "roomType":        room.room_type.type_name if room and room.room_type else None,
        "propertyId":      prop.id if prop else None,
        "propertyName":    prop.property_name if prop else None,
        "propertyAddress": prop.property_address if prop else None,
        "date":            slot.availability.date.strftime("%Y-%m-%d"),
        "startTime":       slot.start_time.strftime("%H:%M"),
        "endTime":         slot.end_time.strftime("%H:%M"),
        "slotId":          slot.id,
        "status":          appt.status,
        "createdAt":       appt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "initiatedBy":     appt.initiated_by,
        "lastUpdatedBy":   appt.last_updated_by,
    }
    return Response(
        ResponseData.success(result, "Appointment booked successfully."),
        status=status.HTTP_201_CREATED
    )
