from django.utils import timezone
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.contrib.contenttypes.models import ContentType
from appointments.consumers import AppointmentRepository
from appointments.models import AppointmentBookingModel
from landlord.models import LandlordBasePreferenceModel, LandlordDetailsModel, LandlordPropertyDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilityModel, LandlordAvailabilitySlotModel
from localization.models import CityModel, CountryModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from user.fetch_match_details import compute_personality_match
from .models import LandlordInterestRequestModel, TenantInterestRequestModel
from landlord.views import build_all_tabs
from django.db.models import Q


class TenantInterestRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.tenant_id = None
        self.room_id = None

    async def disconnect(self, close_code):
        if self.tenant_id and self.room_id:
            group_name = f"tenant_{self.tenant_id}_room_{self.room_id}"
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data):
        try:
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
            if action == "connection_established":
                # Assuming you have self.bed_id and self.tenant_id already set.
                result = await self.get_bed_statuses_for_tenant(self.room_id, self.tenant_id)
                print(f'result44 {result}')
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "connection_established",
                    "result": result,
                }))
            elif action == "send_interest_request_to_landlord":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                property_id = await self.get_property_id(bed_id)
                result = await self.send_interest_request_to_landlord(tenant_id,bed_id,property_id)
                print(f'result123 {result}')
                bed_group = f"property_{property_id}_bed_{bed_id}"
                prop_group = f"property_{property_id}"

                for group in (bed_group, prop_group):
                    print(f"Sending notification to group {group}")
                    await self.channel_layer.group_send(
                        group,
                        {
                            "type": "send_request_to_landlord_notification",
                            "message": result
                        }
                    )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "interest_request_sent_to_landlord",
                    "result": [result],
                }))
            elif action == "cancel_interest_request_sent_to_landlord":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.cancel_invitation_sent_to_landlord(tenant_id,bed_id)
                print(f'result123 {result}')
                property_id = await self.get_property_id(bed_id)
                landlord_group = f"property_{property_id}_bed_{bed_id}"
                print(f'landlord_group {landlord_group}')
                await self.channel_layer.group_send(
                    landlord_group,
                    {
                        "type": "cancel_interest_request_sent_to_landlord_notification",  # This will trigger the corresponding method in the tenant consumer.
                        "message": result
                    }
                )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "cancelled_interest_request_sent_to_landlord",
                    "result": [result],
                }))
            elif action == "close_conversation_request_from_tenant":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                message = data.get("message","")
                result = await self.close_conversation_request_from_tenant(tenant_id,bed_id,message)
                print(f'result123 {result}')
                property_id = await self.get_property_id(bed_id)
                landlord_group = f"property_{property_id}_bed_{bed_id}"
                print(f'landlord_group {landlord_group}')
                await self.channel_layer.group_send(
                    landlord_group,
                    {
                        "type": "request_closed_notification_to_landlord",  
                        "message": result
                    }
                )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "closed_request_by_tenant",
                    "message": [result],
                }))
            elif action in ["accept_landlord_interest", "reject_landlord_interest"]:
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                message = data.get("message", "")
                result = await self.landlord_interest_request(tenant_id, bed_id, action.split("_")[0], message)
                if "error" in result:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": result["error"]
                    }))
                else:
                    property_id = await self.get_property_id(bed_id)
                    bed_group = f"property_{property_id}_bed_{bed_id}"
                    prop_group = f"property_{property_id}"

                    for group in (bed_group, prop_group):
                        print(f"Sending notification to group {group}")
                        await self.channel_layer.group_send(
                            group,
                            {
                                "type": "tenant_respond_landlord_request_notification",
                                "message": result
                            }
                        )
                    await self.send(text_data=json.dumps({
                        "status": "success",
                        "action": "tenant_respond_landlord_request",
                        "message": [result],
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

    async def landlord_interest_notification_to_tenant(self, event):
        message = event['message']
        print(f"landlord_interest_notification_to_tenant received: {message}")
        result = await self.get_bed_statuses_for_tenant(-1, message['id'])
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "landlord_interest_notification_to_tenant",
            "message": result,
        }))

    async def landlord_cancelled_invitation_notification_to_tenant(self, event):
        message = event['message']
        print(f"landlord_cancelled_invitation_notification_to_tenant received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "landlord_cancelled_invitation_notification_to_tenant",
            "message": [message],
        }))

    async def tenant_interest_response_notification(self, event):
        message = event['message']
        print(f"tenant_interest_response_notification received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "tenant_interest_response_notification",
            "message": [message],
        }))
       
    async def request_closed_by_landlord_notification_to_tenant(self, event):
        message = event['message']
        print(f"request_closed_by_landlord_notification_to_tenant received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "request_closed_by_landlord_notification_to_tenant",
            "message": [message],
        })) 

    async def appointment_booking_request_created_by_tenant(self, event):
        message = event['message']
        print(f"appointment_booking_request_created_by_tenant received: {message}")
        result = await self.get_bed_statuses_for_tenant(message[0], message[1])
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "appointment_booking_request_created_by_tenant",
            "message": result,
        })) 

    async def appointment_request_confirmed_by_landlord(self, event):
        message = event['message']
        print(f"appointment_booking_request_created_by_tenant received: {message}")
        result = await self.get_bed_statuses_for_tenant(message[0], message[1])
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "appointment_request_confirmed_by_landlord",
            "message": result,
        })) 
    
    
    @database_sync_to_async
    def get_property_id(self,bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        return bed.room.property.id
     
    @database_sync_to_async
    def cancel_invitation_sent_to_landlord(self, tenant_id, bed_id):
        try:
            req = TenantInterestRequestModel.objects.get(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False
            )
            req.is_active = False
            req.is_deleted = True
            req.save()
            return {
                "bed_id": bed_id,
                "interest_status": '',
                "message": '',
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : False
            }
        except TenantInterestRequestModel.DoesNotExist:
            return {"error": "No active request found."}
        except Exception as e:
            return {"error": str(e)}
        
    @database_sync_to_async
    def send_interest_request_to_landlord(self, tenant_id, bed_id,property_id):
        try:
            bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        except LandlordRoomWiseBedModel.DoesNotExist:
            return {"error": "Bed not found."}

        # Check if an interest request already exists for this tenant and bed.
        existing = TenantInterestRequestModel.objects.filter(
            tenant__id=tenant_id,
            bed=bed,
            is_active=True,
            is_deleted=False
        ).exists()

        if existing:
            return {"error": "Interest request already exists."}

        try:
            tenant = TenantDetailsModel.objects.get(id=tenant_id)
        except TenantDetailsModel.DoesNotExist:
            return {"error": "Tenant not found."}

        # Create a new interest request with default status "pending".
        req = TenantInterestRequestModel.objects.create(
            tenant=tenant,
            bed=bed,
            status="pending"  # default status
        )

        return {
            "bed_id": bed.id,
            "tenant_id" : tenant_id,
            'property_id' : property_id,
            "interest_status": req.status,
            "message": req.landlord_message,  # likely empty by default
            "is_initiated_by_landlord": False  # tenant initiated this request
        }

    @database_sync_to_async
    def get_bed_statuses_for_tenant(self, room_id, tenant_id):
        print(f"get_bed_statuses_for_tenant called with room_id={room_id}, tenant_id={tenant_id}")
        result = []

        # 1) Determine which beds to include
        if room_id != -1:
            print("→ room_id != -1: fetching beds for specific room")
            beds = LandlordRoomWiseBedModel.objects.filter(
                room_id=room_id,
                is_active=True,
                is_deleted=False
            )
        else:
            print("→ room_id == -1: gathering all beds with any interest for this tenant")
            tenant_bed_ids = list(TenantInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                is_active=True,
                is_deleted=False
            ).values_list('bed_id', flat=True))
            print(f"   tenant_bed_ids: {tenant_bed_ids}")

            landlord_bed_ids = list(LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                is_active=True,
                is_deleted=False
            ).values_list('bed_id', flat=True))
            print(f"   landlord_bed_ids: {landlord_bed_ids}")

            all_bed_ids = set(tenant_bed_ids) | set(landlord_bed_ids)
            print(f"   combined bed IDs: {all_bed_ids}")

            beds = LandlordRoomWiseBedModel.objects.filter(
                id__in=all_bed_ids,
                is_active=True,
                is_deleted=False
            )

        print(f"→ Total beds to process: {beds.count()}")

        # Get tenant's personality details once
        try:
            tenant_persona = TenantPersonalityDetailsModel.objects.get(
                tenant_id=tenant_id,
                is_active=True,
                is_deleted=False
            )
        except TenantPersonalityDetailsModel.DoesNotExist:
            tenant_persona = None
            print("   → No tenant personality details found")

        # Personality matching setup
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]
        max_marks = 10
        total_possible = len(personality_fields) * max_marks

        # 2) For each bed, find any interest request + appointment if accepted
        for bed in beds:
            print(f"\nProcessing bed id={bed.id}, bed_number={bed.bed_number}")
            print(f'appt.bedfvfsvdsvvv {bed.id}')
            # Get landlord's preference answers for this bed
            landlord_answers_qs = list(bed.tenant_preference_answers.all())
            if not landlord_answers_qs:
                base_pref = LandlordBasePreferenceModel.objects.filter(
                    landlord_id=bed.room.property.landlord.id
                ).first()
                if base_pref:
                    landlord_answers_qs = list(base_pref.answers.all())

            # Calculate personality match percentage if tenant has persona
            """match_pct = 0.0
            if tenant_persona and landlord_answers_qs:
                total_score = 0
                for field in personality_fields:
                    ans_id = getattr(tenant_persona, f"{field}_id", None)
                    if not ans_id:
                        continue

                    # landlord's answers for this question
                    try:
                        model_field = TenantPersonalityDetailsModel\
                                        ._meta.get_field(field)\
                                        .remote_field.model
                        ctype = ContentType.objects.get_for_model(model_field)
                        lan_for_field = [
                            la for la in landlord_answers_qs
                            if la.question.content_type == ctype
                        ]
                    except Exception:
                        lan_for_field = []

                    if not lan_for_field:
                        continue

                    sorted_las = sorted(lan_for_field,
                                    key=lambda la: la.preference or 0)
                    idx = next((i for i, la in enumerate(sorted_las)
                            if la.object_id == ans_id), None)
                    if idx is None:
                        continue

                    opts = len(sorted_las)
                    total_score += ((opts - idx) / opts) * max_marks

                match_pct = round((total_score / total_possible) * 100, 2) \
                        if total_possible else 0.0
                print(f"   → Personality match percentage: {match_pct}%")"""
            overall, breakdown = compute_personality_match(tenant_persona, landlord_answers_qs)
            print("Overall match:", overall)
            for field, pct in breakdown.items():
                print(f" • {field}: {pct}%")
            # check interest
            tenant_req = TenantInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed=bed,
                is_active=True,
                is_deleted=False
            ).first()
            landlord_req = LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed=bed,
                is_active=True,
                is_deleted=False
            ).first()

            if tenant_req:
                interest_status = tenant_req.status
                message = tenant_req.landlord_message
                shown_by_landlord = False
                print(f"   → Found tenant_req: status={interest_status}")
            elif landlord_req:
                interest_status = landlord_req.status
                message = landlord_req.tenant_message
                shown_by_landlord = True
                print(f"   → Found landlord_req: status={interest_status}")
            else:
                interest_status = ""
                message = ""
                shown_by_landlord = False
                print("   → No interest request found")

            # check for any appointment
            appt = AppointmentBookingModel.objects.filter(
                tenant__id=tenant_id,
                bed=bed,
                is_active=True,
                is_deleted=False
            ).first()
            if appt:
                print(f"   → Existing appointment found (id={appt.id})")
                # if we're in global mode (room_id == -1), skip this bed entirely
                if room_id == -1:
                    print("   → Skipping this bed because room_id == -1 and appointment exists")
                    continue

            appointment_details = None
            if appt:
                slot = appt.time_slot
                appointment_details = {
                    "appointment_id": appt.id,
                    "slot_id": slot.id,
                    "date": slot.availability.date.strftime('%Y-%m-%d'),
                    "start_time": slot.start_time.strftime('%I:%M %p'),
                    "end_time": slot.end_time.strftime('%I:%M %p'),
                    "status": appt.status,
                }
                print(f"   → Appointment details: {appointment_details}")
            city_obj = CityModel.objects.filter(id=bed.room.property.property_city.id).first()
            print(f'city_obj {city_obj}')
            currency_symbol = (
                city_obj.state.country.currency_symbol
                if city_obj and city_obj.state and city_obj.state.country else ""
            )
            entry = {
                "bed_id": bed.id,
                "landlord_id" : bed.room.property.landlord.id,
                "property_id" : bed.room.property.id,
                "bed_number": bed.bed_number,
                "room_name" : bed.room.room_name,
                "is_active": bed.is_active,
                "tenant_preference": bed.tenant_preference,
                "price": str(bed.rent_amount) + f' {currency_symbol}',
                "rent_type" : 'Month' if bed.is_rent_monthly else 'Day',
                "interest_status": interest_status,
                "message": message,
                "is_initiated_by_landlord": shown_by_landlord,
                "appointment_details": appointment_details,
                "personality_match_percentage": overall,  # Added this field
                'details_of_personality_match' : breakdown
            }
            result.append(entry)

        print(f"\nget_bed_statuses_for_tenant returning {len(result)} entries")
        return result


    @database_sync_to_async
    def get_landlord_interest_request(self, tenant_id, room_id):
        result = []
        bed_ids = LandlordRoomWiseBedModel.objects.filter(room_id=room_id).values_list('id', flat=True)
        for bed_id in bed_ids:
            request_qs = LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False
            )
            if request_qs.exists():
                req = request_qs.first()
                landlord_request_data = {
                    "bed_id": bed_id,
                    "status": req.status,
                    "tenant_message": req.tenant_message,
                }
                result.append(landlord_request_data)
        print(f'result123 {result}')
        return result
    
    @database_sync_to_async
    def landlord_interest_request(self, tenant_id, bed_id, status, message):
        try:
            print(f'status {status}')
            req = LandlordInterestRequestModel.objects.get(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False
            )
            req.tenant_message = message
            if status == 'accept':
                req.accept()
            else:
                req.reject()
            print({
                "bed_id": bed_id,
                "interest_status": req.status,
                "message": req.tenant_message,
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : True
            })
            return {
                "bed_id": bed_id,
                "interest_status": req.status,
                "message": req.tenant_message,
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : True
            }
        except LandlordInterestRequestModel.DoesNotExist:
            print('Interest request not found')
            return {"error": "Interest request not found."}


    @database_sync_to_async
    def tenant_interest_request(self, tenant_id, bed_id, status, message):
        try:
            print(f'status {status}')
            req = TenantInterestRequestModel.objects.get(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False
            )
            req.landlord_message = message
            if status == 'accept':
                req.accept()
            else:
                req.reject()
            tenant = req.tenant
            tenant_data = {
                "id": tenant.id,
                "first_name": tenant.first_name,
                "last_name": tenant.last_name,
                "bed_id" : bed_id,
                "date_of_birth": str(tenant.date_of_birth) if tenant.date_of_birth else "",
                "interest_status": req.status,
                "landlord_message": req.landlord_message,
            }
            return {
                "status": "success",
                "action": "tenant_interest_request_notification",
                "bed_id": bed_id,
                "tenant_data": tenant_data
            }
        except TenantInterestRequestModel.DoesNotExist:
            print('Interest request not found')
            return {"error": "Interest request not found."}

    @database_sync_to_async
    def close_conversation_request_from_tenant(self, tenant_id, bed_id,message):
        try:
            # Try to find a request in LandlordInterestRequestModel
            req = LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_deleted=False
            ).first()
            # If not found, try in TenantInterestRequestModel
            if not req:
                req = TenantInterestRequestModel.objects.filter(
                    tenant__id=tenant_id,
                    bed__id=bed_id,
                    is_deleted=False
                ).first()

            
            if req:
                # Close the conversation.
                req.is_active = False
                req.request_closed_by = "tenant"
                # If your model has a close() method that sets the status to "closed",
                # call that; otherwise, set the status manually.
                try:
                    req.close()  # calls the model's close() method (if defined)
                except AttributeError:
                    req.status = "closed"
                req.save()
                return {
                    "bed_id": bed_id,
                    "interest_status": "closed",
                    "message": message,
                    "tenant_id": tenant_id,
                    "request_closed_by" : "tenant",
                    # Indicate if the closed request was originally initiated by landlord
                    "is_initiated_by_landlord": True if isinstance(req, LandlordInterestRequestModel) else False,
                }
            else:
                return {"error": "No active invitation found."}
        except Exception as e:
            return {"error": str(e)}

class LandlordInterestRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.bed_id = None
        self.property_id = None

    async def disconnect(self, close_code):
        if self.property_id and self.bed_id:
            group_name = f"property_{self.property_id}_bed_{self.bed_id}"
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            print(f'text_data {text_data}')
            action = data.get("action")
            print(f'action {action} {data}')
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
                return
            # Set landlord and bed id if provided
            if "bed_id" in data:
                self.bed_id = data["bed_id"]
            if "room_id" in data:
                self.room_id = data["room_id"]
            if "property_id" in data:
                self.property_id = data["property_id"]
            if "landlord_id" in data:
                self.landlord_id = data["landlord_id"]
            if "includeMatchingTenants" in data:
                self.includeMatchingTenants = data["includeMatchingTenants"]
            if self.bed_id != -1 and self.property_id and self.landlord_id:
                group_name = f"property_{self.property_id}_bed_{self.bed_id}"
                print(f'Joining group: {group_name}')
                await self.channel_layer.group_add(group_name, self.channel_name)
            if self.bed_id == -1 and self.property_id and self.landlord_id:
                group_name = f"property_{self.property_id}"
                print(f'Joining group: {group_name}')
                await self.channel_layer.group_add(group_name, self.channel_name)
            if action == "connection_established":
                result = await self.get_active_tenants(self.room_id,self.bed_id,self.landlord_id,self.property_id,self.includeMatchingTenants)
                print(f'result {result}')
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "connection_established",
                    "message": result,
                }))
            elif action == "send_invitation_to_tenant":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.invitation_to_tenant(tenant_id,bed_id)
                print(f'result123 {result}')
                room_id = await self.get_room_id_for_bed(bed_id)
                room_group = f"tenant_{tenant_id}_room_{room_id}"
                tenant_in_interest_group = f"tenant_{tenant_id}"

                for group in (room_group, tenant_in_interest_group):
                    print(f"Sending notification to group {group}")
                    await self.channel_layer.group_send(
                        group,
                        {
                            "type": "landlord_interest_notification_to_tenant",
                            "message": result
                        }
                    )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "invitation_sent_to_tenant",
                    "message": result,
                }))
            elif action == "cancel_invitation_sent_to_tenant":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.cancel_invitation_sent_to_tenant(tenant_id,bed_id)
                print(f'result123 {result}')
                room_id = await self.get_room_id_for_bed(bed_id)
                print(f'room_id {room_id}')
                tenant_group = f"tenant_{tenant_id}_room_{room_id}"
                print(f'tenant_group {tenant_group}')
                await self.channel_layer.group_send(
                    tenant_group,
                    {
                        "type": "landlord_cancelled_invitation_notification_to_tenant",  # This will trigger the corresponding method in the tenant consumer.
                        "message": result
                    }
                )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "landlord_cancelled_invitation_sent_to_tenant",
                    "message": result,
                }))
            elif action == "close_conversation_request_from_landlord":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.close_conversation_request_from_landlord(tenant_id,bed_id)
                print(f'result123 {result}')
                room_id = await self.get_room_id_for_bed(bed_id)
                print(f'room_id {room_id}')
                tenant_group = f"tenant_{tenant_id}_room_{room_id}"
                print(f'tenant_group {tenant_group}')
                await self.channel_layer.group_send(
                    tenant_group,
                    {
                        "type": "request_closed_by_landlord_notification_to_tenant",  # This will trigger the corresponding method in the tenant consumer.
                        "message": result
                    }
                )
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "conversation_closed_from_landlord",
                    "message": result,
                }))
            elif action == "accept_appointment_request_of_tenant":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.accept_appointment_request_of_tenant(tenant_id,bed_id)
                print(f'result123 {result}')
                room_id = await self.get_room_id_for_bed(bed_id)
                print(f'room_id {room_id}')
                tenant_group = f"tenant_{tenant_id}_room_{room_id}"
                print(f'tenant_group {tenant_group}')
                await self.channel_layer.group_send(
                    tenant_group,
                    {
                        "type": "appointment_request_confirmed_by_landlord",  # This will trigger the corresponding method in the tenant consumer.
                        "message": [room_id,tenant_id]
                    }
                )
                specific_tenant_result = await self.get_tenant_details(tenant_id,bed_id)
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "appointment_request_confirmed_by_landlord",
                    "message": specific_tenant_result,
                }))
            elif action in ["accept_tenant_interest", "reject_tenant_interest"]:
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                message = data.get("message", "")
                result = await self.tenant_interest_request(tenant_id, bed_id, action.split("_")[0], message)
                print(f'resultdd {result}')
                if "error" in result:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": result["error"]
                    }))
                elif bed_id != -1:
                    room_id = await self.get_room_id_for_bed(bed_id)
                    # Use the bed-specific group name
                    tenant_room_group = f"tenant_{tenant_id}_room_{room_id}"
                    tenant_group = f"tenant_{tenant_id}"
                    for group in (tenant_room_group, tenant_group):
                        print(f"Sending notification to group {group}")
                        await self.channel_layer.group_send(
                            group,
                            {
                                "type": "tenant_interest_response_notification",
                                "message": result
                            }
                        )

                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "response_of_tenant_interest_request",
                    "message": result,
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



    async def send_request_to_landlord_notification(self, event):
        message = event['message']
        print(f"send_request_to_landlord_notification received: {message}")
        result = await self.get_active_tenants(bed_id=message['bed_id'],tenant_id=message['tenant_id'],property_id=message['property_id'])
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "send_request_to_landlord_notification",
            "message": result,
        }))
        
    async def cancel_interest_request_sent_to_landlord_notification(self, event):
        message = event['message']
        print(f"cancel_interest_request_sent_to_landlord_notification received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "cancelled_interest_request_sent_to_landlord_notification",
            "message": message,
        }))

    async def landlord_interest_request_notification(self, event):
        message = event['message']
        print(f"landlord_interest_request_notification received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "landlord_interest_request_notification",
            "message": message,
        }))

    async def appointment_created_notification_by_tenant(self, event):
        message = event['message']
        print(f'appointment_created_notification_by_tenant recieved {event}')
        """
        Called when TenantAppointmentConsumer pushes an 'appointment_created' event
        """
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "appointment_created_notification_by_tenant",
            "message": message,
        }))
        
    async def tenant_respond_landlord_request_notification(self, event):
        message = event['message']
        print(f"tenant_respond_landlord_request_notification received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "tenant_respond_landlord_request_notification",
            "message": message,
        }))
        
    async def request_closed_notification_to_landlord(self, event):
        message = event['message']
        print(f"request_closed_notification_to_landlord received: {message}")
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "request_closed_notification_to_landlord",
            "message": message,
        })) 

    async def appointment_booking_request_created_by_tenant(self, event):
        message = event['message']
        print(f"appointment_booking_request_created_by_tenant received for landlord: {message}")
        result = await self.get_tenant_details(message[0],message[1])
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "appointment_booking_request_created_by_tenant",
            "message": result,
        })) 

    @database_sync_to_async
    def accept_appointment_request_of_tenant(self, tenant_id, bed_id):
        try:
            # Fetch the appointment request for the given tenant and bed
            appointment = AppointmentBookingModel.objects.get(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False,
                initiated_by='tenant',
                status='pending'  # Ensure we're only confirming pending appointments
            )

            # Update the appointment status to 'confirmed' and set initiated_by to 'tenant'
            appointment.status = 'confirmed'
            appointment.save()

            # Return success response
            return {
                "appointment_id": appointment.id,
                "tenant_id": tenant_id,
                "bed_id": bed_id,
                "initiated_by": "tenant",
                "appointment_status": appointment.status,
            }
        except AppointmentBookingModel.DoesNotExist:
            return {"error": "No pending appointment request found for the given tenant and bed."}
        except Exception as e:
            return {"error": str(e)}
    
    @database_sync_to_async
    def get_room_id_for_bed(self,bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        return bed.room.id

    @database_sync_to_async
    def get_tenant_details(self, tenant_id, bed_id):
        try:
            # Fetch the specific tenant
            tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True, is_deleted=False)
        except TenantDetailsModel.DoesNotExist:
            return {}

        try:
            # Fetch the specific bed
            bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        except LandlordRoomWiseBedModel.DoesNotExist:
            return {}

        # First, try to get an active tenant-initiated request.
        tenant_req = TenantInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()

        # If no active tenant request exists, try to get a closed one.
        if not tenant_req:
            tenant_req = TenantInterestRequestModel.objects.filter(
                tenant=tenant,
                bed=bed,
                is_deleted=False,
                is_active=False,
                status="closed"
            ).first()

        # Similarly for landlord-initiated requests.
        landlord_req = LandlordInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()

        if not landlord_req:
            landlord_req = LandlordInterestRequestModel.objects.filter(
                tenant=tenant,
                bed=bed,
                is_deleted=False,
                is_active=False,
                status="closed"
            ).first()

        if tenant_req:
            interest_status = tenant_req.status
            message = tenant_req.landlord_message
            interest_shown_by = "tenant"
            request_closed_by = getattr(tenant_req, "request_closed_by", "")
        elif landlord_req:
            interest_status = landlord_req.status
            message = landlord_req.tenant_message
            interest_shown_by = "landlord"
            request_closed_by = getattr(landlord_req, "request_closed_by", "")
        else:
            interest_status = ""
            message = ""
            interest_shown_by = ""
            request_closed_by = ""

        # Initialize appointment details as None
        appointment_details = None

        # Fetch appointment details only if interest_status is accepted
        if interest_status.lower() == "accepted":
            appointment = AppointmentBookingModel.objects.filter(
                tenant=tenant,
                landlord=bed.room.property.landlord,
                bed=bed,
                is_deleted=False
            ).first()  # Get the first valid appointment if exists

            if appointment:
                appointment_details = {
                    "appointment_id": appointment.id,
                    "start_time": appointment.time_slot.start_time.strftime('%H:%M'),
                    "end_time": appointment.time_slot.end_time.strftime('%H:%M'),
                    "status": appointment.status
                }

        tenant_data = {
            "tenant_id": tenant.id,
            "first_name": tenant.first_name,
            "last_name": tenant.last_name,
            "date_of_birth": str(tenant.date_of_birth) if tenant.date_of_birth else "",
            "interest_status": interest_status,
            "message": message,
            "bed_id": bed_id,
            "request_closed_by": request_closed_by,
            "is_initiated_by_landlord": True if interest_shown_by == 'landlord' else False,
        }

        # Add appointment details only if it exists
        if appointment_details:
            tenant_data["appointment_details"] = appointment_details

        tenant_data

        print(f'tenant_data {tenant_data}')
        return tenant_data


    @database_sync_to_async
    def get_active_tenants(self,
                        room_id=-1,
                        bed_id=-1,
                        landlord_id=-1,
                        property_id=-1,
                        includeMatchingTenants=False,
                        tenant_id=-1):
        print(room_id)
        print(bed_id)
        print(landlord_id)
        print(property_id)
        print(includeMatchingTenants)
        print(tenant_id)
        """
        includeMatchingTenants=False:
        Return all interest requests (tenant‐ and landlord‐initiated)
        for bed/room/property, with personality match, skipping booked.
        includeMatchingTenants=True:
        Return only tenants who have NO existing interest request
        on the SPECIFIC bed_id (must be != -1), with personality match.
        tenant_id >= 0:
        Short‐circuit to only that tenant’s records at the DB level.
        """
        result = []

        # 1) Determine bed list & filter
        if bed_id != -1:
            bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
            beds = [bed]
            bed_filter = Q(bed=bed)
        elif room_id != -1:
            beds = list(LandlordRoomWiseBedModel.objects.filter(
                room_id=room_id,
                is_deleted=False,
                is_active=True
            ))
            bed = None
            bed_filter = Q(bed__in=beds)
        else:
            beds = list(LandlordRoomWiseBedModel.objects.filter(
                room__property_id=property_id,
                is_deleted=False,
                is_active=True
            ))
            bed = None
            bed_filter = Q(bed__in=beds)

        # 2) Early tenant_id filter
        tenant_filter = Q()
        if tenant_id != -1:
            tenant_filter = Q(tenant_id=tenant_id)

        # 3) Load all real interest requests on those beds, and only for the tenant if specified
        tenant_requests = list(TenantInterestRequestModel.objects.filter(
            bed_filter, is_deleted=False
        ).filter(tenant_filter))

        landlord_requests = list(LandlordInterestRequestModel.objects.filter(
            bed_filter, is_deleted=False
        ).filter(tenant_filter))

        # 4) Prepare landlord’s preference answers once
        landlord_answers_qs = []
        if beds:
            landlord_answers_qs = list(beds[0].tenant_preference_answers.all())
        if not landlord_answers_qs:
            base_pref = LandlordBasePreferenceModel.objects.filter(
                landlord_id=landlord_id
            ).first()
            if base_pref:
                landlord_answers_qs = list(base_pref.answers.all())

        # 5) Build the `combined` list
        if includeMatchingTenants:
            if bed_id == -1:
                raise ValueError("includeMatchingTenants=True requires a specific bed_id")

            existing_ids = {
                tr.tenant_id for tr in tenant_requests
            } | {
                lr.tenant_id for lr in landlord_requests
            }

            personas = TenantPersonalityDetailsModel.objects.filter(
                is_active=True, is_deleted=False
            ).select_related("tenant")

            # still filter by tenant_id if given
            combined = [
                ("matching", ten_persona)
                for ten_persona in personas
                if ten_persona.tenant.id not in existing_ids
                and (tenant_id == -1 or ten_persona.tenant.id == tenant_id)
            ]
        else:
            combined = (
                [("tenant_req", tr) for tr in tenant_requests] +
                [("landlord_req", lr) for lr in landlord_requests]
            )

        # 6) As a safety, also drop any that slipped through that don’t match tenant_id
        if tenant_id != -1:
            combined = [
                (tag, payload) for tag, payload in combined
                if getattr(payload, 'tenant', payload).id == tenant_id
            ]

        # 7) Common personality‐matching setup
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]
        max_marks = 10
        total_possible = len(personality_fields) * max_marks

        # 8) Process each entry in `combined`
        for tag, payload in combined:
            if tag == "matching":
                ten_persona = payload
                tenant = ten_persona.tenant
                status = ""
                message = ""
                bed_obj = bed
            else:
                req = payload
                tenant = req.tenant
                status = req.status
                message = (req.landlord_message if tag == "tenant_req"
                        else req.tenant_message)
                bed_obj = req.bed

                if status.lower() == "accepted":
                    appt_q = AppointmentBookingModel.objects.filter(
                        Q(bed__in=beds) if bed_id == -1 else Q(bed=bed),
                        tenant=tenant,
                        landlord_id=landlord_id,
                        is_deleted=False
                    )
                    if appt_q.exists():
                        continue

                try:
                    ten_persona = TenantPersonalityDetailsModel.objects.get(
                        tenant=tenant, is_active=True, is_deleted=False
                    )
                except TenantPersonalityDetailsModel.DoesNotExist:
                    ten_persona = None

            """total_score = 0
            if ten_persona:
                for field in personality_fields:
                    ans_id = getattr(ten_persona, f"{field}_id", None)
                    if not ans_id:
                        continue

                    try:
                        model_field = TenantPersonalityDetailsModel._meta\
                                        .get_field(field).remote_field.model
                        ctype = ContentType.objects.get_for_model(model_field)
                        lan_for_field = [
                            la for la in landlord_answers_qs
                            if la.question.content_type == ctype
                        ]
                    except Exception:
                        lan_for_field = []

                    if not lan_for_field:
                        continue

                    sorted_las = sorted(lan_for_field,
                                        key=lambda la: la.preference or 0)
                    idx = next((i for i, la in enumerate(sorted_las)
                                if la.object_id == ans_id), None)
                    if idx is None:
                        continue

                    opts = len(sorted_las)
                    total_score += ((opts - idx) / opts) * max_marks

            match_pct = (round((total_score / total_possible) * 100, 2)
                        if total_possible else 0.0)"""
            overall, breakdown = compute_personality_match(ten_persona, landlord_answers_qs)
            print("Overall match:", overall)
            for field, pct in breakdown.items():
                print(f" • {field}: {pct}%")
            td = {
                "id": tenant.id,
                "first_name": tenant.first_name,
                "last_name": tenant.last_name,
                "tenant_profile_picture":
                    tenant.profile_picture.url if tenant.profile_picture else None,
                "date_of_birth": str(tenant.date_of_birth) or "",
                "interest_status": status,
                "message": message,
                "rent_type" : 'Month' if bed_obj.is_rent_monthly else 'Day',
                "bed_id": bed_obj.id if bed_obj else None,
                "request_closed_by": getattr(payload, "request_closed_by", ""),
                "is_initiated_by_landlord": (tag == "landlord_req"),
                "personality_match_percentage": overall,
                'details_of_personality_match' : breakdown
            }
            if bed_obj:
                city_obj = CityModel.objects.filter(id=bed_obj.room.property.property_city.id).first()
                print(f'city_obj {city_obj}')
                currency_symbol = (
                    city_obj.state.country.currency_symbol
                    if city_obj and city_obj.state and city_obj.state.country else ""
                )
                td["bed_number"] = bed_obj.bed_number
                td["room_name"] = bed_obj.room.room_name
                td["rent_amount"] = str(bed_obj.rent_amount) + f' {currency_symbol}'

            result.append(td)

        # 9) sort by match % desc
        result.sort(key=lambda x: x["personality_match_percentage"], reverse=True)
        return result


    @database_sync_to_async
    def invitation_to_tenant(self, tenant_id, bed_id):
        # Check if an active invitation already exists
        existing = LandlordInterestRequestModel.objects.filter(
            tenant__id=tenant_id,
            bed__id=bed_id,
            is_active=True,
            is_deleted=False
        ).exists()

        if existing:
            return {"error": "Invitation already exists."}

        try:
            # Retrieve the tenant and bed objects
            tenant = TenantDetailsModel.objects.get(id=tenant_id)
            bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)

            # Create a new invitation record with a pending status
            req = LandlordInterestRequestModel.objects.create(
                tenant=tenant,
                bed=bed,
                status='pending',  # default status
            )

            request_update = {
                "bed_id": bed_id,
                "interest_status": req.status,
                "message": req.tenant_message,
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : True
            }

            return request_update
        except Exception as e:
            return {"error": str(e)}

    @database_sync_to_async
    def close_conversation_request_from_landlord(self, tenant_id, bed_id):
        try:
            # Try to find a request in LandlordInterestRequestModel
            req = LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_deleted=False
            ).first()
            # If not found, try in TenantInterestRequestModel
            if not req:
                req = TenantInterestRequestModel.objects.filter(
                    tenant__id=tenant_id,
                    bed__id=bed_id,
                    is_deleted=False
                ).first()
            
            if req:
                # Close the conversation.
                req.is_active = False
                req.request_closed_by = "landlord"
                # If your model has a close() method that sets the status to "closed",
                # call that; otherwise, set the status manually.
                try:
                    req.close()  # calls the model's close() method (if defined)
                except AttributeError:
                    req.status = "closed"
                req.save()
                return {
                    "bed_id": bed_id,
                    "interest_status": "closed",
                    "message": "",
                    "tenant_id": tenant_id,
                    "request_closed_by" : "landlord",
                    # Indicate if the closed request was originally initiated by landlord
                    "is_initiated_by_landlord": True if isinstance(req, LandlordInterestRequestModel) else False,
                }
            else:
                return {"error": "No active invitation found."}
        except Exception as e:
            return {"error": str(e)}

        
    @database_sync_to_async
    def cancel_invitation_sent_to_tenant(self, tenant_id, bed_id):
        try:
            req = LandlordInterestRequestModel.objects.get(
                tenant__id=tenant_id,
                bed__id=bed_id,
                is_active=True,
                is_deleted=False
            )
            req.status = 'closed'
            req.is_active = False
            req.is_deleted = True
            req.save()
            return {
                "bed_id": bed_id,
                "interest_status": '',
                "message": '',
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : None
            }
        except LandlordInterestRequestModel.DoesNotExist:
            return {"error": "No active invitation found."}
        except Exception as e:
            return {"error": str(e)}


    @database_sync_to_async
    def tenant_interest_request(self, tenant_id, bed_id, status, message):
        try:
            print(f'status {status}')
            req = TenantInterestRequestModel.objects.filter(
                Q(bed_id=bed_id) if bed_id != -1 else Q(),
                tenant_id=tenant_id,
                is_active=True,
                is_deleted=False
            ).first()
            print(f'reqff {req}')
            req.landlord_message = message
            if status == 'accept':
                req.accept()
            else:
                req.reject()
            print({
                "bed_id": bed_id,
                "interest_status": req.status,
                "message": req.landlord_message,
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : False,
            })
            return {
                "bed_id": bed_id,
                "interest_status": req.status,
                "message": req.landlord_message,
                "tenant_id" : tenant_id,
                "is_initiated_by_landlord" : False,
            }
        except TenantInterestRequestModel.DoesNotExist:
            print('Interest request not found')
            return {"error": "Interest request not found."}
