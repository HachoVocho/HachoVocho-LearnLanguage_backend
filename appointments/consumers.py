
from django.utils import timezone
from datetime import timedelta
from channels.db import database_sync_to_async
from .models import AppointmentBookingModel
from landlord.models import LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel, LandlordAvailabilityModel
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel
import json
from channels.generic.websocket import AsyncWebsocketConsumer

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
                "roomNumber": room.room_name if room else None,
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
    def fetch_landlord_appointments(landlord_id, property_id, filters=None):
        qs = AppointmentBookingModel.objects.filter(
            landlord_id=landlord_id,
            bed__room__property__id=property_id,
            is_active=True,
            is_deleted=False,
        )

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

            tenant_id = filters.get("tenantId")
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)

            bed_id = filters.get("bedId")
            if bed_id:
                qs = qs.filter(bed_id=bed_id)

        qs = qs.order_by(
            "time_slot__availability__date",
            "time_slot__start_time"
        )

        out = []
        for appt in qs:
            slot = appt.time_slot
            out.append({
                "appointmentId": appt.id,
                "tenantFirstName": appt.tenant.first_name,
                "tenantLastName": appt.tenant.last_name,
                "bedId": appt.bed.id,
                "tenantId": appt.tenant.id,
                "bedNumber": appt.bed.bed_number,
                "date": slot.availability.date.strftime("%Y-%m-%d"),
                "startTime": slot.start_time.strftime("%H:%M"),
                "endTime": slot.end_time.strftime("%H:%M"),
                "status": appt.status,
                "slotId": slot.id,
                "initiatedBy": appt.initiated_by,
                'lastUpdatedBy' : appt.last_updated_by
            })

        priority = {'pending': 0, 'confirmed': 1, 'cancelled': 2}
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
        today = timezone.now().date()
        end = today + timedelta(days=10)
        qs = (LandlordAvailabilityModel.objects
              .filter(landlord_id=landlord_id,
                      property_id=property_id,
                      date__range=[today, end],
                      is_active=True,
                      is_deleted=False)
              .prefetch_related("time_slots"))

        out = []
        for av in qs:
            slots = av.time_slots.filter(is_active=True, is_deleted=False)
            out.append({
                "date": av.date.strftime("%Y-%m-%d"),
                "slots": [
                    {
                        "slotId": s.id,
                        "startTime": s.start_time.strftime("%H:%M"),
                        "endTime": s.end_time.strftime("%H:%M")
                    }
                    for s in slots
                ]
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
    async def connect(self):
        await self.accept()
        self.tenant_id = None

    async def disconnect(self, close_code):
        if self.tenant_id:
            await self.channel_layer.group_discard(f"tenant_{self.tenant_id}", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        print(f'actiondd {action} {data}')
        if action == "get_tenant_appointments":
            self.tenant_id = data.get("tenant_id")
            # join group so future pushes can target tenant_<id>
            await self.channel_layer.group_add(f"tenant_{self.tenant_id}", self.channel_name)
            appointments = await AppointmentRepository.fetch_tenant_appointments(self.tenant_id)
            await self.send(text_data=json.dumps({
                "status": "success",
                "action": "get_tenant_appointments",
                "data": appointments
            }))
        # ─── CANCEL ──────────────────────────────────────────────
        elif action == "cancel_appointment_by_tenant":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status":"error",
                    "message":"appointment_id required"
                })
            res = await AppointmentRepository.cancel_appointment(appt_id,'tenant')
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type":"appointment_cancelled","message":res}
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
        elif action == "book_appointment_slot":
            tenant_id   = data.get("tenant_id")
            bed_id      = data.get("bed_id")
            slot_id     = data.get("slot_id")
            landlord_id = data.get("landlord_id")

            result = await AppointmentRepository.create_appointment(
                tenant_id, bed_id, slot_id, landlord_id,'tenant'
            )

            # ack back to landlord
            await self.send_json({
                "status": "success",
                "action": "appointment_booking_request_created_by_landlord",
                "message": result,
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
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type":"appointment_rescheduled","message":res}
            )
            await self.send_json({
                "action": "reschedule_appointment_by_tenant",
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
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {
                  "type": "appointment_confirmed",
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



class LandlordAppointmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.landlord_id = None
        self.property_id = None

    async def disconnect(self, close_code):
        if self.landlord_id and self.property_id:
            await self.channel_layer.group_discard(
                f"landlord_{self.landlord_id}_property_{self.property_id}",
                self.channel_name
            )

    async def receive(self, text_data):
        data   = json.loads(text_data)
        action = data.get("action")
        print(f'actiondd {action}')
        # capture landlord & property if provided
        if "landlord_id"  in data:
            self.landlord_id  = data["landlord_id"]
        if "property_id"  in data:
            self.property_id  = data["property_id"]

        # join the group so updates can be broadcast
        if self.landlord_id and self.property_id:
            await self.channel_layer.group_add(
                f"landlord_{self.landlord_id}_property_{self.property_id}",
                self.channel_name
            )

        # ─── LIST & FILTER ───────────────────────────────────────
        if action == "get_landlord_appointments":
            appts = await AppointmentRepository.fetch_landlord_appointments(self.landlord_id,
                                           self.property_id,
                                           filters=None)
            print(f'apptsdd {appts}')
            await self.send_json({
                "action": "get_landlord_appointments",
                "data": appts
            })

        elif action == "filter_landlord_appointments":
            # expects { filters: { status, dateFrom, dateTo, tenantId?, bedId? } }
            filters = data.get("filters", {})
            appts = await AppointmentRepository.fetch_landlord_appointments(self.landlord_id,
                                           self.property_id,
                                           filters=filters)
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
                tenant_id, bed_id, slot_id, landlord_id,'landlord'
            )

            # ack back to landlord
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
                    "status":"error",
                    "message":"appointment_id required"
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
                    "status":"error",
                    "message":"propertyId required"
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
                    "status":"error",
                    "message":"appointment_id required"
                })
            res = await AppointmentRepository.cancel_appointment(appt_id,'landlord')
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type":"appointment_cancelled","message":res}
            )
            await self.send_json({
                "action": "cancel_appointment_by_landlord",
                "data": res
            })

        elif action == "decline_appointment_by_landlord":
            appt_id = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status":"error",
                    "message":"appointment_id required"
                })
            res = await AppointmentRepository.decline_appointment(appt_id,'landlord')
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type":"appointment_cancelled","message":res}
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
                    "status":"error",
                    "message":"appointment_id & slotId required"
                })
            res = await AppointmentRepository.reschedule_appointment(appt_id, slot_id,'landlord')
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {"type":"appointment_rescheduled","message":res}
            )
            await self.send_json({
                "action": "reschedule_appointment_by_landlord",
                "data": res
            })
        # ─── CONFIRM ─────────────────────────────────────────────
        elif action == "confirm_appointment_by_landlord":
            appt_id   = data.get("appointment_id")
            if not appt_id:
                return await self.send_json({
                    "status": "error",
                    "message": "appointment_id required"
                })
            # perform the confirm
            res = await AppointmentRepository.confirm_appointment(appt_id,'landlord')
            # notify tenant
            await self.channel_layer.group_send(
                f"tenant_{res['tenantId']}_room_{res['roomId']}",
                {
                  "type": "appointment_confirmed",
                  "message": res
                }
            )
            # ack back to landlord
            await self.send_json({
                "action": "confirm_appointment_by_landlord",
                "data": res
            })

        else:
            await self.send_json({
                "status":"error",
                "message":f"Unknown action {action}"
            })

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

