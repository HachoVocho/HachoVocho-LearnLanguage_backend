# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now

from notifications.send_notifications import send_onesignal_notification
from user.fetch_match_details import compute_personality_match

from .models import AppointmentBookingModel
from .serializers import BookAppointmentSerializer, GetAppointmentsSerializer
from landlord.models import LandlordBasePreferenceModel, LandlordDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication


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
    try:
        tenant_persona = TenantPersonalityDetailsModel.objects.get(
            tenant_id=tenant.id,
            is_active=True,
            is_deleted=False
        )
    except TenantPersonalityDetailsModel.DoesNotExist:
        tenant_persona = None
    print("   → No tenant personality details found")
    landlord_answers_qs = list(bed.tenant_preference_answers.all())
    if not landlord_answers_qs:
        base_pref = LandlordBasePreferenceModel.objects.filter(
            landlord_id=bed.room.property.landlord.id
        ).first()
        if base_pref:
            landlord_answers_qs = list(base_pref.answers.all())

    overall, breakdown = compute_personality_match(tenant_persona, landlord_answers_qs)
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
        'landlordFirstName' : landlord.first_name,
        'landlordLastName' : landlord.last_name,
        "personality_match_percentage": overall,  # Added this field
        'details_of_personality_match' : breakdown
    }
    
    send_onesignal_notification(
        landlord_ids=[appt.landlord.id],
        headings={"en": "Appointment Booking Request"},
        contents={"en": f"Tenant {appt.tenant.first_name} {appt.tenant.last_name} sent you appointment booking request for this slot {appt.time_slot} "},
        data={"appointment_id": appt.id, "type": "landlord_appointment"},
    )
    return Response(
        ResponseData.success(result, "Appointment booked successfully."),
        status=status.HTTP_201_CREATED
    )
