from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json

from appointments.models import AppointmentBookingModel
from landlord.models import LandlordRoomWiseBedModel
from tenant.models import TenantDetailsModel
from .models import LandlordInterestRequestModel, TenantInterestRequestModel
from landlord.views import build_all_tabs

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
            # Set landlord and bed id if provided
            if "tenant_id" in data:
                self.tenant_id = data["tenant_id"]
            if "room_id" in data:
                self.room_id = data["room_id"]
            if self.tenant_id and self.room_id:
                group_name = f"tenant_{self.tenant_id}_room_{self.room_id}"
                print(f'Joining group: {group_name}')
                await self.channel_layer.group_add(group_name, self.channel_name)
            if action == "connection_established":
                # Assuming you have self.bed_id and self.tenant_id already set.
                result = await self.get_bed_statuses_for_tenant(self.room_id, self.tenant_id)
                await self.send(text_data=json.dumps({
                    "status": "success",
                    "action": "connection_established",
                    "result": result,
                }))
            elif action == "send_interest_request_to_landlord":
                tenant_id = data.get("tenant_id")
                bed_id = data.get("bed_id")
                result = await self.send_interest_request_to_landlord(tenant_id,bed_id)
                print(f'result123 {result}')
                property_id = await self.get_property_id(bed_id)
                landlord_group = f"property_{property_id}_bed_{bed_id}"
                print(f'landlord_group {landlord_group}')
                await self.channel_layer.group_send(
                    landlord_group,
                    {
                        "type": "send_request_to_landlord_notification",  # This will trigger the corresponding method in the tenant consumer.
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
                    # Use the bed-specific group name
                    group_name = f"property_{property_id}_bed_{bed_id}"
                    await self.channel_layer.group_send(
                        group_name,
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
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "landlord_interest_notification_to_tenant",
            "message": [message],
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
    def get_room_id_for_bed(self,bed_id):
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        return bed.room.id
    
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
    def send_interest_request_to_landlord(self, tenant_id, bed_id):
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
            "interest_status": req.status,
            "message": req.landlord_message,  # likely empty by default
            "is_initiated_by_landlord": False  # tenant initiated this request
        }

    @database_sync_to_async
    def get_bed_statuses_for_tenant(self, room_id, tenant_id):
        result = []
        # Retrieve all beds in the given room
        beds = LandlordRoomWiseBedModel.objects.filter(room_id=room_id)
        
        for bed in beds:
            # Check for a tenant-initiated interest request for this bed
            tenant_req = TenantInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed=bed,
                is_active=True,
                is_deleted=False
            ).first()

            # Check for a landlord-initiated interest request for this bed
            landlord_req = LandlordInterestRequestModel.objects.filter(
                tenant__id=tenant_id,
                bed=bed,
                is_active=True,
                is_deleted=False
            ).first()

            if tenant_req:
                interest_status = tenant_req.status
                message = tenant_req.landlord_message
                interest_shown_by = "tenant"
            elif landlord_req:
                interest_status = landlord_req.status
                message = landlord_req.tenant_message
                interest_shown_by = "landlord"
            else:
                interest_status = ""
                message = ""
                interest_shown_by = ""

            appointment_details = None
            # Only if status is accepted then check for an appointment
            if interest_status and interest_status.lower() == "accepted":
                # Assuming accepted means the appointment is confirmed
                appointment = AppointmentBookingModel.objects.filter(
                    tenant__id=tenant_id,
                    bed=bed,
                    is_active=True,
                    is_deleted=False,
                ).first()
                if appointment:
                    appointment_details = {
                        "appointment_id": appointment.id,
                        "start_time": appointment.time_slot.start_time.strftime('%I:%M %p'),
                        "end_time": appointment.time_slot.end_time.strftime('%I:%M %p'),
                        "status": appointment.status
                    }
            
            result.append({
                "bed_id": bed.id,
                "interest_status": interest_status,
                "message": message,
                "is_initiated_by_landlord": interest_shown_by == "landlord",
                "appointment_details": appointment_details
            })
        print(f'get_bed_statuses_for_tenant result: {result}')
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
            # Set landlord and bed id if provided
            if "bed_id" in data:
                self.bed_id = data["bed_id"]
            if "property_id" in data:
                self.property_id = data["property_id"]
            if self.bed_id and self.property_id:
                group_name = f"property_{self.property_id}_bed_{self.bed_id}"
                print(f'Joining group: {group_name}')
                await self.channel_layer.group_add(group_name, self.channel_name)
            if action == "connection_established":
                result = await self.get_active_tenants(self.bed_id)
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
                print(f'room_id {room_id}')
                tenant_group = f"tenant_{tenant_id}_room_{room_id}"
                print(f'tenant_group {tenant_group}')
                await self.channel_layer.group_send(
                    tenant_group,
                    {
                        "type": "landlord_interest_notification_to_tenant",  # This will trigger the corresponding method in the tenant consumer.
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
                if "error" in result:
                    await self.send(text_data=json.dumps({
                        "status": "error",
                        "message": result["error"]
                    }))
                else:
                    room_id = await self.get_room_id_for_bed(bed_id)
                    # Use the bed-specific group name
                    group_name = f"tenant_{tenant_id}_room_{room_id}"
                    await self.channel_layer.group_send(
                        group_name,
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
        await self.send(text_data=json.dumps({
            "status": "success",
            "action": "send_request_to_landlord_notification",
            "message": message,
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
    def get_active_tenants(self, bed_id):
        result = []
        try:
            bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
        except LandlordRoomWiseBedModel.DoesNotExist:
            return result

        # Fetch all active tenants
        tenants = TenantDetailsModel.objects.filter(is_active=True, is_deleted=False)

        for tenant in tenants:
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
                "id": tenant.id,
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

            result.append(tenant_data)

        print(f'result123 {result}')
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
