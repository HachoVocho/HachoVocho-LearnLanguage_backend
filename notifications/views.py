# help_support/views.py (or notifications/views.py)

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions    import IsAuthenticated, AllowAny
from rest_framework.authentication         import SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models      import TenantDeviceNotificationModel, LandlordDeviceNotificationModel
from .serializers import TenantDeviceRegistrationSerializer, LandlordDeviceRegistrationSerializer
from response     import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from tenant.models   import TenantDetailsModel
from landlord.models import LandlordDetailsModel
from .models      import (
    NotificationTypeModel,
    TenantNotificationSettingModel,
    LandlordNotificationSettingModel,
)
from .serializers import (
    TenantNotificationToggleSerializer,
    LandlordNotificationToggleSerializer,
    TenantNotificationListSerializer,
    LandlordNotificationListSerializer,
)

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def register_tenant_device(request):
    """
    Register or update a tenant's OneSignal player_id.
    - If the same player_id already exists and is active: do nothing.
    - If a different active record exists: deactivate it, then create a new one.
    """
    ser = TenantDeviceRegistrationSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    tenant_id = ser.validated_data['tenant_id']
    new_pid   = ser.validated_data['player_id']

    tenant = get_object_or_404(TenantDetailsModel, id=tenant_id, is_active=True)

    # Deactivate any other active registrations for this tenant with a different player_id
    TenantDeviceNotificationModel.objects.filter(
        tenant=tenant,
        is_active=True
    ).exclude(player_id=new_pid).update(is_active=False, is_deleted=True)

    # Check if an active record already exists for this tenant+player_id
    obj, created = TenantDeviceNotificationModel.objects.get_or_create(
        tenant=tenant,
        player_id=new_pid,
        defaults={'is_active': True, 'is_deleted': False}
    )
    if not created and not obj.is_active:
        # It existed but was previously deactivated — re-activate it
        obj.is_active = True
        obj.is_deleted = False
        obj.save()

    msg = "registered" if created or not obj.is_active else "already registered"
    return Response(
        ResponseData.success_without_data(f"Tenant device {msg}"),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def register_landlord_device(request):
    """
    Register or update a landlord's OneSignal player_id.
    - If the same player_id already exists and is active: do nothing.
    - If a different active record exists: deactivate it, then create a new one.
    """
    ser = LandlordDeviceRegistrationSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    landlord_id = ser.validated_data['landlord_id']
    new_pid     = ser.validated_data['player_id']

    landlord = get_object_or_404(LandlordDetailsModel, id=landlord_id, is_active=True)

    # Deactivate any other active registrations for this landlord with a different player_id
    LandlordDeviceNotificationModel.objects.filter(
        landlord=landlord,
        is_active=True
    ).exclude(player_id=new_pid).update(is_active=False, is_deleted=True)

    # Check if an active record already exists for this landlord+player_id
    obj, created = LandlordDeviceNotificationModel.objects.get_or_create(
        landlord=landlord,
        player_id=new_pid,
        defaults={'is_active': True, 'is_deleted': False}
    )
    if not created and not obj.is_active:
        # It existed but was previously deactivated — re-activate it
        obj.is_active = True
        obj.is_deleted = False
        obj.save()

    msg = "registered" if created or not obj.is_active else "already registered"
    return Response(
        ResponseData.success_without_data(f"Landlord device {msg}"),
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def toggle_tenant_notification(request):
    ser = TenantNotificationToggleSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error(ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    tenant_id, nt_id, state = (
        ser.validated_data['tenant_id'],
        ser.validated_data['notification_type_id'],
        ser.validated_data['is_enabled'],
    )

    tenant = get_object_or_404(TenantDetailsModel, id=tenant_id, is_active=True)
    nt     = get_object_or_404(NotificationTypeModel, id=nt_id)

    setting, created = TenantNotificationSettingModel.objects.get_or_create(
        tenant=tenant,
        notification_type=nt,
        defaults={'is_enabled': state}
    )
    if not created:
        setting.is_enabled = state
        setting.save()

    msg = f"Tenant notification '{nt.code}' set to {'On' if state else 'Off'}"
    return Response(
        ResponseData.success_without_data(msg),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_tenant_notifications(request):
    ser = TenantNotificationListSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error(ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    tenant_id = ser.validated_data['tenant_id']
    tenant = get_object_or_404(TenantDetailsModel, id=tenant_id, is_active=True)

    # 1) existing settings for this tenant
    qs = TenantNotificationSettingModel.objects.filter(
        tenant=tenant
    ).select_related('notification_type')

    # 2) which master types apply to tenants and are not yet set
    existing_type_ids = set(qs.values_list('notification_type_id', flat=True))
    missing_types = NotificationTypeModel.objects.filter(
        code__startswith='tenant_'
    ).exclude(
        id__in=existing_type_ids
    )

    # 3) create only those missing tenant_* types
    if missing_types.exists():
        TenantNotificationSettingModel.objects.bulk_create([
            TenantNotificationSettingModel(
                tenant=tenant,
                notification_type=nt,
                is_enabled=True
            )
            for nt in missing_types
        ])
        qs = TenantNotificationSettingModel.objects.filter(
            tenant=tenant
        ).select_related('notification_type')

    # 4) serialize and return
    data = [{
        'notification_type_id': s.notification_type.id,
        'code':                s.notification_type.code,
        'name':                s.notification_type.name,
        'description':         s.notification_type.description,
        'is_enabled':          s.is_enabled,
    } for s in qs]

    return Response(
        ResponseData.success(data, "Tenant notification settings fetched"),
        status=status.HTTP_200_OK
    )



@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def toggle_landlord_notification(request):
    ser = LandlordNotificationToggleSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error(ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    landlord_id, nt_id, state = (
        ser.validated_data['landlord_id'],
        ser.validated_data['notification_type_id'],
        ser.validated_data['is_enabled'],
    )

    landlord = get_object_or_404(LandlordDetailsModel, id=landlord_id, is_active=True)
    nt       = get_object_or_404(NotificationTypeModel, id=nt_id)

    setting, created = LandlordNotificationSettingModel.objects.get_or_create(
        landlord=landlord,
        notification_type=nt,
        defaults={'is_enabled': state}
    )
    if not created:
        setting.is_enabled = state
        setting.save()

    msg = f"Landlord notification '{nt.code}' set to {'On' if state else 'Off'}"
    return Response(
        ResponseData.success_without_data(msg),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_landlord_notifications(request):
    ser = LandlordNotificationListSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error(ser.errors),
                        status=status.HTTP_400_BAD_REQUEST)

    landlord_id = ser.validated_data['landlord_id']
    landlord = get_object_or_404(LandlordDetailsModel, id=landlord_id, is_active=True)

    qs = LandlordNotificationSettingModel.objects.filter(landlord=landlord) \
                                                .select_related('notification_type')
    # 2) which master types apply to tenants and are not yet set
    existing_type_ids = set(qs.values_list('notification_type_id', flat=True))
    missing_types = NotificationTypeModel.objects.filter(
        code__startswith='landlord_'
    ).exclude(
        id__in=existing_type_ids
    )

    # 3) create only those missing tenant_* types
    if missing_types.exists():
        LandlordNotificationSettingModel.objects.bulk_create([
            LandlordNotificationSettingModel(
                landlord=landlord,
                notification_type=nt,
                is_enabled=True
            )
            for nt in missing_types
        ])
    print(f'sdvsdvsvqs {qs}')
    data = [{
        'notification_type_id': s.notification_type.id,
        'code':                s.notification_type.code,
        'name':                s.notification_type.name,
        'description':         s.notification_type.description,
        'is_enabled':          s.is_enabled,
    } for s in qs]

    return Response(
        ResponseData.success(data, "Landlord notification settings fetched"),
        status=status.HTTP_200_OK
    )