# dashboard/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from interest_requests.models import LandlordInterestRequestModel, TenantInterestRequestModel
from .models import LandlordDetailsModel
from landlord.models import LandlordPropertyDetailsModel
from appointments.models import AppointmentBookingModel
from chat.models import ChatMessageModel
from django.contrib.auth.models import AnonymousUser
from user.ws_auth import authenticate_websocket

class LandlordDashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("[LandlordDashboardConsumer] connect() called")
        # Accept immediately, then authenticate on first message
        await self.accept()
        print("[LandlordDashboardConsumer] connection accepted")
        self.landlord = None
        user, error = await authenticate_websocket(self.scope)
        print(f"[LandlordDashboardConsumer] authenticate_websocket returned: user={user}, error={error}")
        if isinstance(user, AnonymousUser):
            print(f"[LandlordDashboardConsumer] auth failed: {error}")
            return await self.close(code=4001)
        # hold user for later
        self.landlord = user
        print(f"[LandlordDashboardConsumer] authenticated as: {user}")
        # join group for future broadcasts
        group_name = f"landlord_dashboard_{self.landlord.id}"
        await self.channel_layer.group_add(
            group_name, self.channel_name
        )
        print(f"[LandlordDashboardConsumer] added to group: {group_name}")

    async def receive_json(self, content):
        print(f"[LandlordDashboardConsumer] receive_json: {content}")
        # Expect first message: {"action": "init", "landlord_id": X}
        if content.get("action") == "init":
            landlordId = content.get("landlord_id")
            print(f"[LandlordDashboardConsumer] init requested for landlord_id={landlordId}")
            # validate Landlord matches authenticated user
            if landlordId != self.landlord.id:
                print(f"[LandlordDashboardConsumer] landlord_id mismatch: {landlordId} vs {self.landlord.id}")
                return await self.close(code=4001)
            try:
                self.landlord = await LandlordDetailsModel.objects.aget(
                    pk=landlordId, is_active=True
                )
                print(f"[LandlordDashboardConsumer] loaded LandlordDetailsModel for id={landlordId}")
            except LandlordDetailsModel.DoesNotExist:
                print(f"[LandlordDashboardConsumer] LandlordDetailsModel.DoesNotExist for id={landlordId}")
                return await self.close(code=4001)

            # send initial counts
            await self.send_counts()

    async def refresh_counts(self, event):
        """
        handler for when some other consumer tells us to re-push the latest counts.
        """
        print("[LandlordDashboardConsumer] refresh_counts event received")
        await self.send_counts()
        
    async def send_counts(self):
        print(f"[LandlordDashboardConsumer] send_counts() for Landlord={self.landlord.id}")
        l = self.landlord

        # 2) Interest-request count by this Landlord
        t_reqs = await TenantInterestRequestModel.objects.filter(
            bed__room__property__landlord=l,
            is_active=True, is_deleted=False
        ).exclude(status='accepted').acount()

        # 2) Landlord-initiated requests
        l_reqs = await LandlordInterestRequestModel.objects.filter(
            bed__room__property__landlord=l,
            is_active=True, is_deleted=False
        ).exclude(status='accepted').acount()

        total_reqs = t_reqs + l_reqs
        print(f"[LandlordDashboardConsumer] tenant_reqs={t_reqs}, landlord_reqs={l_reqs}, total={total_reqs}")

        # 3) Pending appointments for this Landlord
        appts = await AppointmentBookingModel.objects.filter(
            landlord=l, status="pending", is_active=True, is_deleted=False
        ).acount()
        print(f"[LandlordDashboardConsumer] pending_appointments count: {appts}")

        # 4) Unread chat messages sent to this Landlord
        chat_unread = await ChatMessageModel.objects.filter(
            receiver=f"landlord:{l.id}",
            is_read=False,
            is_active=True,
            is_deleted=False
        ).acount()
        print(f"[LandlordDashboardConsumer] unread_chats count: {chat_unread}")

        # push the counts_update payload
        payload = {
            "action": "counts_update",
            "data": {
                "matching_tenants": total_reqs,
                "interest_requests": total_reqs,
                "pending_appointments": appts,
                "unread_chats": chat_unread,
            }
        }
        print(f"[LandlordDashboardConsumer] sending counts payload: {payload}")
        await self.send_json(payload)

    async def disconnect(self, code):
        print(f"[LandlordDashboardConsumer] disconnect(code={code}) called")
        if self.landlord:
            group_name = f"Landlord_dashboard_{self.landlord.id}"
            await self.channel_layer.group_discard(
                group_name, self.channel_name
            )
            print(f"[LandlordDashboardConsumer] removed from group: {group_name}")
