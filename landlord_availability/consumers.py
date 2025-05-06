import json
from datetime import datetime, timedelta
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import LandlordAvailabilityModel
from landlord.models import LandlordRoomWiseBedModel
# Make sure to import AppointmentBookingModel from the correct app:
from tenant.models import TenantDetailsModel  # if AppointmentBookingModel is in the tenant app
from landlord_availability.models import LandlordAvailabilitySlotModel
from appointments.models import AppointmentBookingModel  # update 'your_app' to the actual app name
from django.db.models import Q
from django.utils.timezone import now

class LandlordAvailabilityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.tenant_id = None
        self.bed_id = None

    async def disconnect(self, close_code):
        if self.tenant_id and self.bed_id:
            group_name = f"tenant_{self.tenant_id}_bed_{self.bed_id}"
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")
            print(f'action {action} {data}')
            # Set tenant and bed id if provided
            if "tenant_id" in data:
                self.tenant_id = data["tenant_id"]
            if "bed_id" in data:
                self.bed_id = data["bed_id"]
            if self.tenant_id and self.bed_id:
                group_name = f"tenant_{self.tenant_id}_bed_{self.bed_id}"
                print(f'Joining group: {group_name}')
                await self.channel_layer.group_add(group_name, self.channel_name)

            if action == "connection_established":
                # Fetch availability data for the next 10 days
                availability_data = await self.get_availability_for_next_10_days(self.bed_id)
                print(f'availability_data {availability_data}')
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "connection_established",
                    "data": availability_data,
                }))

            elif action == "get_availability_time_of_landlord":
                print('reached')
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                print(f'data {data}')
                # Fetch availability data for the next 10 days
                availability_data = await self.get_availability_for_next_10_days(bed_id)
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "get_availability_time_of_landlord",
                    "time_slots": availability_data,
                }))

            elif action == "appointment_booking_request_by_tenant":
                print("Processing appointment booking request")
                slot_id = data.get("slot_id")
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                if not slot_id or not tenant_id:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": "slot_id and tenant_id are required"
                    }))
                    return
                appointment = await self.create_appointment_booking(slot_id, tenant_id)
                room_id = await self.get_room_id_for_bed(bed_id)
                property_id = await self.get_property_id_for_bed(bed_id)

                landlord_group = f"property_{property_id}_bed_{bed_id}"
                print(f'landlord_group {landlord_group}')
                await self.channel_layer.group_send(
                    landlord_group,
                    {
                        "type": "appointment_booking_request_created_by_tenant",
                        "message": [tenant_id, bed_id, property_id]
                    }
                )

                tenant_group = f"tenant_{tenant_id}_room_{room_id}"
                print(f'tenant_group {tenant_group}')
                await self.channel_layer.group_send(
                    tenant_group,
                    {
                        "type": "appointment_booking_request_created_by_tenant",
                        "message": [room_id, tenant_id]
                    }
                )

                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "appointment_booking_request_created_by_tenant",
                    "appointment_details": appointment,
                    "message": "Appointment booked successfully"
                }))

            # ───── New cancellation action ─────
            elif action == "cancel_appointment_by_tenant":
                print("Processing appointment cancellation request")
                appointment_id = data.get("appointment_id")
                tenant_id = data.get("tenant_id")
                if not appointment_id or not tenant_id:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": "appointment_id and tenant_id are required"
                    }))
                    return
                # perform your cancellation logic (e.g. await self.cancel_appointment(appointment_id))
                cancellation_result = await self.cancel_appointment(appointment_id)

                # notify any relevant groups (if needed)
                await self.channel_layer.group_send(
                    f"tenant_{tenant_id}_notifications",
                    {
                        "type": "appointment_cancellation_processed",
                        "message": {
                            "appointment_id": appointment_id,
                            "status": cancellation_result
                        }
                    }
                )

                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "cancel_appointment_by_tenant",
                    "message": "Appointment cancelled successfully",
                    "result": cancellation_result
                }))
            elif action == "confirm_appointment_by_tenant":
                print("Processing appointment confirmation request")
                appointment_id = data.get("appointment_id")
                tenant_id = data.get("tenant_id")
                if not appointment_id or not tenant_id:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": "appointment_id and tenant_id are required"
                    }))
                    return

                # mark it confirmed
                confirm_result = await self.confirm_appointment(appointment_id)

                # notify tenant (and landlord if desired)
                await self.channel_layer.group_send(
                    f"tenant_{tenant_id}_notifications",
                    {
                        "type": "appointment_confirmed",
                        "message": confirm_result
                    }
                )

                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "confirm_appointment_by_tenant",
                    "message": "Appointment confirmed successfully",
                    "result": confirm_result
                }))

            else:
                await self.send(text_data=json.dumps({
                    "status": "error",
                    "message": "Invalid action specified"
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": str(e)
            }))

    @database_sync_to_async
    def confirm_appointment(self, appointment_id):
        """
        Marks an existing AppointmentBookingModel as confirmed.
        """
        try:
            appt = AppointmentBookingModel.objects.get(
                id=appointment_id,
                is_active=True,
                is_deleted=False
            )
        except AppointmentBookingModel.DoesNotExist:
            raise Exception(f"Appointment {appointment_id} not found")

        appt.status = 'confirmed'
        appt.updated_at = now()
        appt.save()

        return {
            "appointment_id": appt.id,
            "status": appt.status
        }

    @database_sync_to_async
    def cancel_appointment(self, appointment_id):
        """
        Marks an existing AppointmentBookingModel as cancelled.
        Returns a dict with the appointment_id and new status,
        or raises an exception if not found.
        """
        try:
            appointment = AppointmentBookingModel.objects.get(
                id=appointment_id,
                is_active=True,
                is_deleted=False
            )
        except AppointmentBookingModel.DoesNotExist:
            raise Exception(f"Appointment {appointment_id} not found")

        appointment.status = 'cancelled'
        appointment.updated_at = now()
        appointment.save()

        return {
            "appointment_id": appointment.id,
            "status": appointment.status
        }


    @database_sync_to_async
    def get_room_id_for_bed(self,bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        return bed.room.id
    
    @database_sync_to_async
    def get_property_id_for_bed(self,bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        return bed.room.property.id
    
    @database_sync_to_async
    def get_landlord_and_property_id(self, bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        print(f'bed123 {bed}')
        landlord_id = bed.room.property.landlord.id
        print(f'landlord_id {landlord_id}')
        property_id = bed.room.property.id
        print(f'property_id {property_id}')
        return landlord_id, property_id


    @database_sync_to_async
    def get_availability_for_next_10_days(self, bed_id):
        print('inside get_availability_for_next_10_days')
        # Get landlord_id and property_id from bed_id
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        print(f'bed: {bed}')
        landlord_id = bed.room.property.landlord.id
        print(f'landlord_id: {landlord_id}')
        property_id = bed.room.property.id
        print(f'property_id: {property_id}')
        
        # Get today's date and the date 10 days from today
        today = timezone.now().date()
        end_date = today + timedelta(days=10)
        print(f'today {today}')
        print(f'end_date {end_date}')
        # Fetch all availabilities for the next 10 days
        availabilities = LandlordAvailabilityModel.objects.filter(
            landlord__id=landlord_id,
            property__id=property_id,
            date__range=[today, end_date],
            is_active=True,
            is_deleted=False
        ).prefetch_related('time_slots')
        print(f'availabilities: {availabilities}')
        
        # Prepare the response data
        availability_data = []
        for availability in availabilities:
            # Get all active time slots for this availability
            time_slots = availability.time_slots.filter(is_active=True, is_deleted=False)
            slots_for_day = []
            for slot in time_slots:
                slots_for_day.append({
                    "slot_id": slot.id,  # include slot id
                    "start_time": slot.start_time.strftime('%I:%M %p'),  # 12-hour format with AM/PM
                    "end_time": slot.end_time.strftime('%I:%M %p'),      # 12-hour format with AM/PM
                })
            availability_data.append({
                "date": availability.date.strftime('%Y-%m-%d'),
                "slots": slots_for_day
            })
            print(f'availability_data so far: {availability_data}')
        
        return availability_data

    @database_sync_to_async
    def create_appointment_booking(self, slot_id, tenant_id):
        """
        Create an AppointmentBookingModel record based on the provided slot_id and tenant_id.
        Retrieves the time slot, landlord from availability, and the bed from self.bed_id.
        """
        # Retrieve the selected time slot
        try:
            slot = LandlordAvailabilitySlotModel.objects.get(id=slot_id, is_active=True, is_deleted=False)
        except LandlordAvailabilitySlotModel.DoesNotExist:
            raise Exception("Time slot not found")
        
        # Retrieve landlord from the slot's availability
        availability = slot.availability
        landlord = availability.landlord
        
        # Retrieve the bed using self.bed_id (set previously)
        if self.bed_id:
            try:
                bed = LandlordRoomWiseBedModel.objects.get(id=self.bed_id)
            except LandlordRoomWiseBedModel.DoesNotExist:
                raise Exception("Bed not found")
        else:
            raise Exception("Bed ID not provided")
        
        # Retrieve tenant instance
        try:
            tenant = TenantDetailsModel.objects.get(id=tenant_id)
        except TenantDetailsModel.DoesNotExist:
            raise Exception("Tenant not found")

        AppointmentBookingModel.objects.filter(
            Q(tenant=tenant, bed=bed) |
            Q(landlord=landlord, bed=bed),
            is_active=True,
            is_deleted=False, 
        ).update(
            status='cancelled',
            updated_at=now()
        )
        # Create the appointment booking record
        appointment = AppointmentBookingModel.objects.create(
            tenant=tenant,
            landlord=landlord,
            bed=bed,
            time_slot=slot,
            initiated_by='tenant',
            status="pending"
        )
        return {
            "appointment_id": appointment.id,
            "bed_id": appointment.bed.id,
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "status": appointment.status
        }
