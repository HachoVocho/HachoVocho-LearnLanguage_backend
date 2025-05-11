
from django.utils import timezone
from datetime import datetime, timedelta
from channels.db import database_sync_to_async

from localization.models import CityModel
from user.fetch_match_details import compute_personality_match
from user.refresh_count_for_groups import refresh_counts_for_groups
from user.ws_auth import authenticate_websocket

from .models import AppointmentBookingModel
from landlord.models import LandlordBasePreferenceModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel, LandlordAvailabilityModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from landlord.models import LandlordDetailsModel
import json
from typing import Optional, Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, TokenError

class AppointmentRepository:
    @staticmethod
    @database_sync_to_async
    def confirm_appointment(appt_id,last_updated_by):
        appt = AppointmentBookingModel.objects.get(
            id=appt_id, is_active=True, is_deleted=False
        )
        appt.status = "confirmed"
        appt.last_updated_by = last_updated_by
        appt.updated_at = timezone.now()
        appt.save()
        return {
            "appointmentId": appt.id,
            "status": appt.status,
            "tenantId": appt.tenant.id,
            "roomId": appt.bed.room.id,
        }

    @staticmethod
    @database_sync_to_async
    def fetch_tenant_appointments(tenant_id, filters=None):
        qs = AppointmentBookingModel.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            is_deleted=False
        ).exclude(status='cancelled', initiated_by='tenant')

        if filters:
            status = filters.get("status")
            if status:
                qs = qs.filter(status=status)

            date_from = filters.get("dateFrom")
            if date_from:
                qs = qs.filter(
                    time_slot__availability__date__gte=date_from
                )

            date_to = filters.get("dateTo")
            if date_to:
                qs = qs.filter(
                    time_slot__availability__date__lte=date_to
                )

            bed_id = filters.get("bedId")
            if bed_id:
                qs = qs.filter(bed_id=bed_id)

            property_id = filters.get("propertyId")
            if property_id:
                qs = qs.filter(bed__room__property_id=property_id)

        qs = qs.order_by(
            "time_slot__availability__date",
            "time_slot__start_time"
        )

        out = []
        for appt in qs:
            slot = appt.time_slot
            bed = appt.bed
            room = bed.room
            property = room.property if room else None
            city_obj = CityModel.objects.filter(id=property.property_city.id).first()
            print(f'city_obj {city_obj}')
            currency_symbol = (
                city_obj.state.country.currency_symbol
                if city_obj and city_obj.state and city_obj.state.country else ""
            )
            out.append({
                "appointmentId": appt.id,
                "landlordId": appt.landlord.id,
                'propertyId' : property.id,
                "landlordFirstName": appt.landlord.first_name,
                "landlordLastName": appt.landlord.last_name,
                "tenantId": appt.tenant.id,
                "bedId": bed.id,
                "bedNumber": bed.bed_number,
                "roomId": room.id if room else None,
                "roomName" : bed.room.room_name,
                "rentAmount" : str(bed.rent_amount) + f' {currency_symbol}',
                "rentType" : 'Month' if bed.is_rent_monthly else 'Day', 
                "roomType": room.room_type.type_name if (room and room.room_type) else None,
                "propertyId": property.id if property else None,
                "propertyName": property.property_name if property else None,
                "propertyAddress": property.property_address if property else None,
                "date": slot.availability.date.strftime("%Y-%m-%d"),
                "startTime": slot.start_time.strftime("%H:%M"),
                "endTime": slot.end_time.strftime("%H:%M"),
                "slotId": slot.id,
                "status": appt.status,
                "createdAt": appt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "initiatedBy": appt.initiated_by,
                'lastUpdatedBy' : appt.last_updated_by
            })

        priority = {'pending': 0, 'confirmed': 1, 'cancelled': 2}
        out.sort(key=lambda x: priority.get(x['status'], 99))
        return out

    @staticmethod
    @database_sync_to_async
    def fetch_landlord_appointments(
        landlord_id: int,
        property_id: Optional[int] = None,
        bed_id: Optional[int]      = None,
        tenant_id: Optional[int]   = None,
        filters: Optional[Dict[str, Any]] = None,
    ):
        # Base queryset
        qs = AppointmentBookingModel.objects.filter(
            landlord_id=landlord_id,
            is_active=True,
            is_deleted=False,
        )

        # Narrow by bed if provided, otherwise by property
        if bed_id is not None:
            qs = qs.filter(bed_id=bed_id)
        elif property_id is not None:
            qs = qs.filter(bed__room__property_id=property_id)
        else:
            raise ValueError("Must supply either property_id or bed_id")

        # Narrow to a specific tenant if given
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)

        # Legacy filters
        if filters:
            status    = filters.get("status")
            date_from = filters.get("dateFrom")
            date_to   = filters.get("dateTo")

            if status:
                qs = qs.filter(status=status)
            if date_from:
                qs = qs.filter(time_slot__availability__date__gte=date_from)
            if date_to:
                qs = qs.filter(time_slot__availability__date__lte=date_to)

        # Order and serialize
        qs = qs.order_by(
            "time_slot__availability__date",
            "time_slot__start_time",
        )
        # Personality matching setup
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]
        max_marks = 10
        total_possible = len(personality_fields) * max_marks
        out = []
        for appt in qs:
            # Get landlord's preference answers for this bed
            print(f'appt.bedfvfv {appt.bed.id}')
            # Get tenant's personality details once
            try:
                tenant_persona = TenantPersonalityDetailsModel.objects.get(
                    tenant_id=appt.tenant.id,
                    is_active=True,
                    is_deleted=False
                )
            except TenantPersonalityDetailsModel.DoesNotExist:
                tenant_persona = None
                print("   → No tenant personality details found")

            landlord_answers_qs = list(appt.bed.tenant_preference_answers.all())
            if not landlord_answers_qs:
                base_pref = LandlordBasePreferenceModel.objects.filter(
                    landlord_id=appt.bed.room.property.landlord.id
                ).first()
                if base_pref:
                    landlord_answers_qs = list(base_pref.answers.all())
            slot = appt.time_slot
            
            overall, breakdown = compute_personality_match(tenant_persona, landlord_answers_qs)
            print("Overall match:", overall)
            for field, pct in breakdown.items():
                print(f" • {field}: {pct}%")
            city_obj = CityModel.objects.filter(id=appt.bed.room.property.property_city.id).first()
            print(f'city_obj {city_obj}')
            currency_symbol = (
                city_obj.state.country.currency_symbol
                if city_obj and city_obj.state and city_obj.state.country else ""
            )
            out.append({
                "appointmentId":   appt.id,
                "tenantId":        appt.tenant.id,
                "tenantFirstName": appt.tenant.first_name,
                "tenantLastName":  appt.tenant.last_name,
                "bedId":           appt.bed.id,
                "bedNumber": appt.bed.bed_number,
                "roomName" : appt.bed.room.room_name,
                "rentAmount" : str(appt.bed.rent_amount) + f' {currency_symbol}',
                "rentType" : 'Month' if appt.bed.is_rent_monthly else 'Day',
                "date":            slot.availability.date.strftime("%Y-%m-%d"),
                "startTime":       slot.start_time.strftime("%H:%M"),
                "endTime":         slot.end_time.strftime("%H:%M"),
                "status":          appt.status,
                "slotId":          slot.id,
                "initiatedBy":     appt.initiated_by,
                "lastUpdatedBy":   appt.last_updated_by,
                "personality_match_percentage": overall,  # Added this field
                'details_of_personality_match' : breakdown
            })

        # Sort by status priority
        priority = {'pending': 0, 'confirmed': 1, 'cancelled': 2, 'declined': 3}
        out.sort(key=lambda x: priority.get(x['status'], 99))
        return out



    @staticmethod
    @database_sync_to_async
    def create_appointment(tenant_id, bed_id, slot_id, landlord_id,initiated_by):
        tenant = TenantDetailsModel.objects.get(id=tenant_id)
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        landlord = LandlordDetailsModel.objects.get(id=landlord_id)
        timeslot = LandlordAvailabilitySlotModel.objects.get(id=slot_id)

        appt = AppointmentBookingModel.objects.create(
            tenant=tenant,
            landlord=landlord,
            bed=bed,
            time_slot=timeslot,
            status="pending",
            initiated_by=initiated_by
        )

        return {
            "appointment_id": appt.id,
            "tenant_id": tenant_id,
            "bed_id": bed_id,
            "slot_id": slot_id,
            "start_time": timeslot.start_time.strftime('%H:%M'),
            "end_time": timeslot.end_time.strftime('%H:%M'),
            "status": appt.status,
            'propertyId' : appt.bed.room.property.id
        }

    @staticmethod
    @database_sync_to_async
    def fetch_appointment_detail(appt_id):
        appt = AppointmentBookingModel.objects.get(
            id=appt_id, is_active=True, is_deleted=False
        )
        slot = appt.time_slot
        bed = appt.bed
        room = bed.room
        city_obj = CityModel.objects.filter(id=room.property.property_city.id).first()
        print(f'city_obj {city_obj}')
        currency_symbol = (
            city_obj.state.country.currency_symbol
            if city_obj and city_obj.state and city_obj.state.country else ""
        )
        return {
            "appointmentId": appt.id,
            "landlordId": appt.landlord.id,
            "landlordFirstName": appt.landlord.first_name,
            "landlordLastName": appt.landlord.last_name,
            "tenantId": appt.tenant.id,
            "tenantFirstName": appt.tenant.first_name,
            "tenantLastName": appt.tenant.last_name,
            "bedId": bed.id,
            "bedNumber": bed.bed_number,
            "roomName" : bed.room.room_name,
            "rentType" : 'Month' if bed.is_rent_monthly else 'Day',
            "rentAmount" : str(bed.rent_amount) + f' {currency_symbol}',
            "roomType": room.room_type.type_name if room.room_type else "",
            "date": slot.availability.date.strftime("%Y-%m-%d"),
            "startTime": slot.start_time.strftime("%H:%M"),
            "endTime": slot.end_time.strftime("%H:%M"),
            "slotId": slot.id,
            "status": appt.status,
            "initiatedBy": appt.initiated_by,
            "createdAt": appt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "propertyName": room.property.property_name if room.property else "",
        }

    @staticmethod
    @database_sync_to_async
    def get_available_slots(property_id, landlord_id):
        now = timezone.now()
        today = now.date()
        end_date = today + timedelta(days=10)

        # get all availabilities in window
        qs = (
            LandlordAvailabilityModel.objects
                .filter(
                    landlord_id=landlord_id,
                    property_id=property_id,
                    date__range=[today, end_date],
                    is_active=True,
                    is_deleted=False,
                )
                # pull in slots pre-joined
                .prefetch_related("time_slots")
        )

        out = []
        for av in qs:
            # filter out slots that are inactive, deleted, or already CONFIRMED
            slots = (
                av.time_slots.filter(
                    is_active=True,
                    is_deleted=False,
                )
                .exclude(
                    slot_appointments__status='confirmed'
                )
            )

            valid_slots = []
            for s in slots:
                # build a timezone‐aware datetime for slot end
                slot_end_dt = timezone.make_aware(
                    datetime.combine(av.date, s.end_time),
                    timezone.get_current_timezone()
                )
                # skip any slot that’s already past
                if slot_end_dt <= now:
                    continue

                valid_slots.append({
                    "slotId": s.id,
                    "startTime": s.start_time.strftime("%H:%M"),
                    "endTime": s.end_time.strftime("%H:%M"),
                })

            if valid_slots:
                out.append({
                    "date": av.date.strftime("%Y-%m-%d"),
                    "slots": valid_slots,
                })

        return out

    @staticmethod
    @database_sync_to_async
    def cancel_appointment(appt_id,last_updated_by):
        appt = AppointmentBookingModel.objects.get(
            id=appt_id, is_active=True, is_deleted=False
        )
        appt.status = "cancelled"
        appt.last_updated_by = last_updated_by
        appt.updated_at = timezone.now()
        appt.save()
        return {
            "appointmentId": appt.id,
            "status": appt.status,
            "tenantId": appt.tenant.id,
            "roomId": appt.bed.room.id,
            "landlordId" : appt.landlord.id,
            "propertyId" : appt.bed.room.property.id,
            'lastUpdatedBy' : appt.last_updated_by
        }

    @staticmethod
    @database_sync_to_async
    def decline_appointment(appt_id,last_updated_by):
        appt = AppointmentBookingModel.objects.get(
            id=appt_id, is_active=True, is_deleted=False
        )
        appt.status = "declined"
        appt.last_updated_by = last_updated_by
        appt.updated_at = timezone.now()
        appt.save()
        return {
            "appointmentId": appt.id,
            "status": appt.status,
            "tenantId": appt.tenant.id,
            "roomId": appt.bed.room.id,
        }
        
    @staticmethod
    @database_sync_to_async
    def reschedule_appointment(appt_id, slot_id,last_updated_by):
        appt = AppointmentBookingModel.objects.get(
            id=appt_id, is_active=True, is_deleted=False
        )
        slot = LandlordAvailabilitySlotModel.objects.get(
            id=slot_id, is_active=True, is_deleted=False
        )
        appt.time_slot = slot
        appt.status = "pending"
        appt.last_updated_by = last_updated_by
        appt.updated_at = timezone.now()
        appt.save()
        return {
            "appointmentId": appt.id,
            "status": appt.status,
            "tenantId": appt.tenant.id,
            "roomId": appt.bed.room.id,
            "slotId": slot.id,
            "date": slot.availability.date.strftime("%Y-%m-%d"),
            "startTime": slot.start_time.strftime("%H:%M"),
            "endTime": slot.end_time.strftime("%H:%M"),
        }
    
    
class TenantAppointmentConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = None  # Initialize as None
        self.room_id = None    # Initialize as None

    async def connect(self):
        try:
            # Initialize room_id (already done in __init__ but can be here too)
            self.room_id = None
            user, error = await authenticate_websocket(self.scope)
            if isinstance(user, AnonymousUser):
                print(f"[WS Auth] failed: {error}")
                return await self.close(code=4001)


            self.scope['user'] = user
            self.tenant_id = user.id  # Now properly initialized
            
            await self.accept()
            await self.send(json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket connected',
                'tenant_id': self.tenant_id
            }))
            
        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close(code=4002)  # Internal error
            raise
        
    async def get_user_from_token(self, token):
        """
        Validate the JWT and return the corresponding user.
        Logs any errors encountered.
        """
        from tenant.models import TenantDetailsModel

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            # assume your “user” is actually TenantDetailsModel
            return await TenantDetailsModel.objects.aget(id=user_id)
        except TokenError as e:
            # Some other token problem
            print(f"[JWT] TokenError: {e}")
        except TenantDetailsModel.DoesNotExist:
            print(f"[JWT] No TenantDetailsModel for user_id {access_token.get('user_id')}")
        except Exception as e:
            # Catch-all for anything unexpected
            print(f"[JWT] Unexpected error in get_user_from_token: {e!r}")

        # On any failure, treat as anonymous
        return AnonymousUser()

    async def disconnect(self, close_code):
        try:
            # Safe access to attributes
            if hasattr(self, 'tenant_id') and self.tenant_id and \
               hasattr(self, 'room_id') and self.room_id:
                await self.channel_layer.group_discard(
                    f'tenant_{self.tenant_id}_room_{self.room_id}',
                    self.channel_name
                )
            elif hasattr(self, 'tenant_id') and self.tenant_id:
                await self.channel_layer.group_discard(
                    f'tenant_{self.tenant_id}',
                    self.channel_name
                )
        except Exception as e:
            print(f"Disconnection error: {str(e)}")
        finally:
            # Clean up
            self.tenant_id = None
            self.room_id = None
            
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        print(f'action {action} {data}')
        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return
        # Set landlord and bed id if provided
        if "tenant_id" in data:
            self.tenant_id = data["tenant_id"]
        if "room_id" in data:
            self.room_id = data["room_id"]
        if self.tenant_id and self.room_id != -1:
            group_name = f"tenant_{self.tenant_id}_room_{self.room_id}"
            print(f'Joining group: {group_name}')
            await self.channel_layer.group_add(group_name, self.channel_name)
        if self.tenant_id and self.room_id == -1:
            group_name = f"tenant_{self.tenant_id}"
            print(f'Joining group: {group_name}')
            await self.channel_layer.group_add(group_name, self.channel_name)
        if action == "get_tenant_appointments":
            appointments = await AppointmentRepository.fetch_tenant_appointments(self.tenant_id)
            await self.send(text_data=json.dumps({
                "status": "success",
                "action": "get_tenant_appointments",
                "data": appointments
            }))
            tenant_group = f"tenant_dashboard_{self.tenant_id}"
            print(f'tenant_group {tenant_group}')
            await refresh_counts_for_groups([tenant_group])
        # ─── CANCEL ──────────────────────────────────────────────
        elif action == "cancel_appointment_by_tenant":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status":"error",
                    "message":"appointment_id required"
                })
            res = await AppointmentRepository.cancel_appointment(appt_id,'tenant')
            # ➋ Notify landlord group
            await self.channel_layer.group_send(
                f"landlord_{res['landlordId']}_property_{res['propertyId']}",
                {
                    "type": "appointment_cancelled_notification_by_tenant",  # event name
                    "message": res,
                }
            )
            await self.send_json({
                "action": "cancel_appointment_by_tenant",
                "data": res
            })
        elif action == "get_available_slots":
            propertyId = data.get("propertyId")
            landlordId = data.get('landlordId')
            if not propertyId:
                return await self.send_json({
                    "status":"error",
                    "message":"propertyId required"
                })
            slots = await AppointmentRepository.get_available_slots(propertyId, landlordId)
            print(f'slots {slots}')
            await self.send_json({
                "action": "get_available_slots",
                "data": slots
            })
        # ─── RESCHEDULE ─────────────────────────────────────────
        elif action == "reschedule_appointment_by_tenant":
            appt_id = data.get("appointment_id")
            slot_id = data.get("slotId")
            if not appt_id or not slot_id:
                return await self.send_json({
                    "status":"error",
                    "message":"appointment_id & slotId required"
                })
            res = await AppointmentRepository.reschedule_appointment(appt_id, slot_id,'tenant')
            # notify landlord
            await self.channel_layer.group_send(
                f"landlord_{res['landlordId']}_property_{res['propertyId']}",
                {"type":"appointment_rescheduled_notification_by_tenant","message":res}
            )
            await self.send_json({
                "action": "appointment_rescheduled_notification_by_tenant",
                "data": res
            })
        # ─── CONFIRM ─────────────────────────────────────────────
        elif action == "confirm_appointment_by_tenant":
            appt_id   = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            # perform the confirm
            res = await AppointmentRepository.confirm_appointment(appt_id,'tenant')
            # ➊ Notify landlord
            await self.channel_layer.group_send(
                f"landlord_{res['landlordId']}_property_{res['roomId']}",  
                {
                    "type": "appointment_confirmed_notification",  # handler name in landlord consumer
                    "message": res
                }
            )
            # ack back to landlord
            await self.send_json({
                "action": "confirm_appointment_by_tenant",
                "data": res
            })
        elif action == "filter_tenant_appointments":
            # expects { filters: { status, dateFrom, dateTo, tenantId?, bedId? } }
            filters = data.get("filters", {})
            appts = await AppointmentRepository.fetch_tenant_appointments(self.tenant_id,
                                           filters=filters)
            await self.send_json({
                "action": "filter_tenant_appointments",
                "data": appts
            })
        else:
            await self.send_json({
                "status":"error",
                "message":f"Unknown action {action}"
            })

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    async def appointment_created(self, event):
        await self.send_json({
            "action": "appointment_booking_request_created_by_tenant",
            "data": event["message"],
        })

    async def appointment_cancelled_notification_by_landlord(self, event):
            await self.send_json({
                "action": "appointment_cancelled_notification_by_landlord",
                "data": event["message"],
            })

    async def appointment_declined_notification_by_landlord(self, event):
            await self.send_json({
                "action": "appointment_declined_notification_by_landlord",
                "data": event["message"],
            })

    async def appointment_confirmed_notification_by_landlord(self, event):
        print(f'appointment_confirmed_notification_by_landlord {event}')
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "appointment_confirmed_notification_by_landlord",
            "data": event["message"],
        }))

    async def appointment_rescheduled(self, event):
        await self.send_json({
            "action": "reschedule_appointment_by_landlord",
            "data": event["message"],
        })
        
class LandlordAppointmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.landlord_id = None
        self.property_id = None
        user, error = await authenticate_websocket(self.scope)
        if isinstance(user, AnonymousUser):
            print(f"[WS Auth] failed: {error}")
            return await self.close(code=4001)


    async def disconnect(self, close_code):
        if self.landlord_id and self.property_id:
            await self.channel_layer.group_discard(
                f"landlord_{self.landlord_id}_property_{self.property_id}",
                self.channel_name
            )

    async def receive(self, text_data):
        data   = json.loads(text_data)
        action = data.get("action")
        print(f'actiondd {action} {data}')
        # capture landlord & property if provided
        if "landlord_id"  in data:
            self.landlord_id  = data["landlord_id"]
        if "property_id"  in data:
            self.property_id  = data["property_id"]
        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return
        # join the group so updates can be broadcast
        if self.landlord_id and self.property_id:
            await self.channel_layer.group_add(
                f"landlord_{self.landlord_id}_property_{self.property_id}",
                self.channel_name
            )

        # ─── LIST & FILTER ───────────────────────────────────────
        if action == "get_landlord_appointments":
            appts = await AppointmentRepository.fetch_landlord_appointments(
                self.landlord_id, self.property_id, filters=None
            )
            await self.send_json({
                "action": "get_landlord_appointments",
                "data": appts
            })
            landlord_group = f"landlord_dashboard_{self.landlord_id}"
            print(f'landlord_group {landlord_group}')
            await refresh_counts_for_groups([landlord_group])

        elif action == "filter_landlord_appointments":
            filters = data.get("filters", {})
            appts = await AppointmentRepository.fetch_landlord_appointments(
                self.landlord_id, self.property_id, filters=filters
            )
            await self.send_json({
                "action": "filter_landlord_appointments",
                "data": appts
            })

        # ─── BOOK ────────────────────────────────────────────────
        elif action == "book_appointment_slot":
            tenant_id   = data.get("tenant_id")
            bed_id      = data.get("bed_id")
            slot_id     = data.get("slot_id")
            landlord_id = data.get("landlord_id")

            result = await AppointmentRepository.create_appointment(
                tenant_id, bed_id, slot_id, landlord_id, 'landlord'
            )
            await self.send_json({
                "status": "success",
                "action": "appointment_booking_request_created_by_landlord",
                "message": result,
            })

        # ─── DETAILS ─────────────────────────────────────────────
        elif action == "get_appointment_details":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            detail = await AppointmentRepository.fetch_appointment_detail(appt_id)
            await self.send_json({
                "action": "get_appointment_details",
                "data": detail
            })

        # ─── AVAILABLE SLOTS ────────────────────────────────────
        elif action == "get_available_slots":
            propertyId = data.get("propertyId")
            landlordId = data.get('landlordId')
            if not propertyId:
                return await self.send_json({
                    "status": "error",
                    "message": "propertyId required"
                })
            slots = await AppointmentRepository.get_available_slots(propertyId, landlordId)
            await self.send_json({
                "action": "get_available_slots",
                "data": slots
            })

        # ─── CANCEL ──────────────────────────────────────────────
        elif action == "cancel_appointment_by_landlord":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            res = await AppointmentRepository.cancel_appointment(appt_id, 'landlord')
            tenant_group = f"tenant_dashboard_{res.get('tenantId')}"
            landlord_group = f"landlord_dashboard_{self.landlord_id}"
            print(f'tenant_group {tenant_group}')
            await refresh_counts_for_groups([tenant_group,landlord_group])
            # notify both tenant groups
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type": "appointment_cancelled_notification_by_landlord", "message": res}
            )
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}",
                {"type": "appointment_cancelled_notification_by_landlord", "message": res}
            )

            await self.send_json({
                "action": "cancel_appointment_by_landlord",
                "data": res
            })

        # ─── DECLINE ─────────────────────────────────────────────
        elif action == "decline_appointment_by_landlord":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            res = await AppointmentRepository.decline_appointment(appt_id, 'landlord')

            # notify both tenant groups
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type": "appointment_declined_notification_by_landlord", "message": res}
            )
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}",
                {"type": "appointment_declined_notification_by_landlord", "message": res}
            )

            await self.send_json({
                "action": "decline_appointment_by_landlord",
                "data": res
            })

        # ─── RESCHEDULE ─────────────────────────────────────────
        elif action == "reschedule_appointment_by_landlord":
            appt_id = data.get("appointment_id")
            slot_id = data.get("slotId")
            if not appt_id or not slot_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id & slotId required"
                })
            res = await AppointmentRepository.reschedule_appointment(
                appt_id, slot_id, 'landlord'
            )
            await self.send_json({
                "action": "reschedule_appointment_by_landlord",
                "data": res
            })

        # ─── CONFIRM ─────────────────────────────────────────────
        elif action == "confirm_appointment_by_landlord":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            res = await AppointmentRepository.confirm_appointment(appt_id, 'landlord')
            print(f"tenant_{res['tenantId']}")
            print(f"tenant_{res['tenantId']}_room_{res['roomId']}")
            print(f'self.channel_layerdc {self.channel_layer}')
            # notify both tenant groups
            for group in (
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                f"tenant_{res['tenantId']}",
            ):
                await self.channel_layer.group_send(
                    group,
                    {"type": "appointment_confirmed_notification_by_landlord", "message": res}
                )

            await self.send_json({
                "action": "confirm_appointment_by_landlord",
                "data": res
            })

        else:
            await self.send_json({
                "status": "error",
                "message": f"Unknown action {action}"
            })


    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    async def appointment_created_notification_by_tenant(self, event):
        print(f'appointment_created_notification_by_tenant recieved {event}')
        """
        Called when TenantAppointmentConsumer pushes an 'appointment_created' event
        """
        appts = await AppointmentRepository.fetch_landlord_appointments(
                event['message']['landlordId'], bed_id=event['message']['bedId'],tenant_id=event['message']['tenantId'], filters=None
            )
        await self.send_json({
            "action": "appointment_created_notification_by_tenant",
            "data": appts,
        })
        
    async def appointment_cancelled_notification_by_tenant(self, event):
        """
        Called when TenantAppointmentConsumer pushes an 'appointment_cancelled' event
        """
        print(f'appointment_cancelled_notification_by_tenant {event}')
        await self.send_json({
            "action": "appointment_cancelled_notification_by_tenant",
            "data": event["message"],
        })
        
    async def appointment_confirmed(self, event):
        """
        Handle a tenant-confirmed appointment.
        """
        await self.send_json({
            "action": "confirm_appointment_by_tenant",
            "data": event["message"],
        })
        
    async def appointment_rescheduled_notification_by_tenant(self, event):
        """
        Receive a reschedule notification from a tenant,
        and forward it to the landlord client.
        """
        await self.send_json({
            "action": "appointment_rescheduled_notification_by_tenant",
            "data": event["message"],
        })