# your_app/utils/notifications.py

import requests
from django.conf import settings
from typing import Optional, List, Dict, Any
from notifications.models import (
    TenantDeviceNotificationModel,
    LandlordDeviceNotificationModel,
    NotificationTypeModel,
    TenantNotificationSettingModel,
    LandlordNotificationSettingModel,
)

ONESIGNAL_API_URL = "https://onesignal.com/api/v1/notifications"


def _filter_ids_by_setting(
    ids: List[int],
    is_tenant: bool,
    nt_code: str
) -> List[int]:
    """
    Return only those IDs (tenant or landlord) that have is_enabled=True
    for the NotificationType with code=nt_code.
    """
    try:
        nt = NotificationTypeModel.objects.get(code=nt_code)
    except NotificationTypeModel.DoesNotExist:
        return []  # No such type => no one should be notified
    print(f'svsvsvsnt {nt.id} {ids}')
    if is_tenant:
        qs = TenantNotificationSettingModel.objects.filter(
            tenant_id__in=ids,
            notification_type=nt,
            is_enabled=True
        )
        print(f'sdvdsvqs {qs}')
        return list(qs.values_list("tenant_id", flat=True))
    else:
        qs = LandlordNotificationSettingModel.objects.filter(
            landlord_id__in=ids,
            notification_type=nt,
            is_enabled=True
        )
        return list(qs.values_list("landlord_id", flat=True))


def _get_player_ids(
    tenant_ids: Optional[List[int]] = None,
    landlord_ids: Optional[List[int]] = None,
    nt_code: Optional[str] = None,
) -> List[str]:
    """
    Get player IDs for given tenant and/or landlord IDs,
    but only those who have enabled the notification type nt_code.
    """
    player_ids: List[str] = []

    # Filter tenant_ids by setting
    if tenant_ids and nt_code:
        tenant_ids = _filter_ids_by_setting(tenant_ids, is_tenant=True, nt_code=nt_code)
    # Now fetch devices for those tenants
    if tenant_ids:
        tenant_devices = TenantDeviceNotificationModel.objects.filter(
            tenant_id__in=tenant_ids,
            is_active=True,
            is_deleted=False
        ).values_list("player_id", flat=True)
        player_ids.extend(list(tenant_devices))

    # Same for landlords
    if landlord_ids and nt_code:
        landlord_ids = _filter_ids_by_setting(landlord_ids, is_tenant=False, nt_code=nt_code)
    if landlord_ids:
        landlord_devices = LandlordDeviceNotificationModel.objects.filter(
            landlord_id__in=landlord_ids,
            is_active=True,
            is_deleted=False
        ).values_list("player_id", flat=True)
        player_ids.extend(list(landlord_devices))

    return player_ids


def send_onesignal_notification(
    *,
    tenant_ids: Optional[List[int]]    = None,
    landlord_ids: Optional[List[int]]  = None,
    player_ids: Optional[List[str]]    = None,  # fallback
    headings: Dict[str, str],
    contents: Dict[str, str],
    data: Optional[Dict[str, Any]]     = None,
    buttons: Optional[List[Dict[str, Any]]] = None,
    large_icon: Optional[str]          = None,
    small_icon: Optional[str]          = None,
    android_channel_id: Optional[str]  = None,
) -> Dict[str, Any]:
    """
    Send a push via OneSignal, but only to users who have
    enabled this notification type.
    The 'data' dict *must* include a "type" key matching NotificationTypeModel.code.
    """

    # Extract the notification-type code
    nt_code = None
    if data and isinstance(data, dict):
        nt_code = data.get("type")
    if not player_ids:
        player_ids = _get_player_ids(
            tenant_ids=tenant_ids,
            landlord_ids=landlord_ids,
            nt_code=nt_code,
        )

    if not player_ids:
        print(f"[OneSignal] No active devices for notification type '{nt_code}', aborting.")
        return {"error": "no_recipients", "details": nt_code}

    payload: Dict[str, Any] = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "include_player_ids": player_ids,
        "headings": headings,
        "contents": contents,
    }

    # Attach optional fields if provided
    for field_name, value in (
        ("data", data),
        ("buttons", buttons),
        ("large_icon", large_icon),
        ("small_icon", small_icon),
        ("android_channel_id", android_channel_id),
    ):
        if value is not None:
            payload[field_name] = value

    headers = {
        "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    print(f"[OneSignal] Sending '{nt_code}' to {len(player_ids)} devices")
    try:
        resp = requests.post(ONESIGNAL_API_URL, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if http_err.response else "N/A"
        print(f"[OneSignal] HTTP Error {status_code}: {http_err}")
        return {"error": "http_error", "details": str(http_err)}
    except Exception as e:
        print(f"[OneSignal] Error: {e}")
        return {"error": "notification_failed", "details": str(e)}
