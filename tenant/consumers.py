# dashboard/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from interest_requests.models import LandlordInterestRequestModel, TenantInterestRequestModel
from tenant.models import TenantDetailsModel
from landlord.models import LandlordPropertyDetailsModel
from appointments.models import AppointmentBookingModel
from chat.models import ChatMessageModel
from django.contrib.auth.models import AnonymousUser
from user.ws_auth import authenticate_websocket

class TenantDashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("[TenantDashboardConsumer] connect() called")
        # Accept immediately, then authenticate on first message
        await self.accept()
        print("[TenantDashboardConsumer] connection accepted")
        self.tenant = None
        user, error = await authenticate_websocket(self.scope)
        print(f"[TenantDashboardConsumer] authenticate_websocket returned: user={user}, error={error}")
        if isinstance(user, AnonymousUser):
            print(f"[TenantDashboardConsumer] auth failed: {error}")
            return await self.close(code=4001)
        # hold user for later
        self.tenant_user = user
        print(f"[TenantDashboardConsumer] authenticated as: {user}")
        # join group for future broadcasts
        group_name = f"tenant_dashboard_{user.id}"
        await self.channel_layer.group_add(
            group_name, self.channel_name
        )
        print(f"[TenantDashboardConsumer] added to group: {group_name}")

    async def receive_json(self, content):
        print(f"[TenantDashboardConsumer] receive_json: {content}")
        # Expect first message: {"action": "init", "tenant_id": X}
        if content.get("action") == "init":
            tid = content.get("tenant_id")
            print(f"[TenantDashboardConsumer] init requested for tenant_id={tid}")
            # validate tenant matches authenticated user
            if tid != self.tenant_user.id:
                print(f"[TenantDashboardConsumer] tenant_id mismatch: {tid} vs {self.tenant_user.id}")
                return await self.close(code=4001)
            try:
                self.tenant = await TenantDetailsModel.objects.aget(
                    pk=tid, is_active=True
                )
                print(f"[TenantDashboardConsumer] loaded TenantDetailsModel for id={tid}")
            except TenantDetailsModel.DoesNotExist:
                print(f"[TenantDashboardConsumer] TenantDetailsModel.DoesNotExist for id={tid}")
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
        print(f"[TenantDashboardConsumer] send_counts() for tenant={self.tenant.id}")
        t = self.tenant

        # 1) Total properties (active & not deleted)
        props = await LandlordPropertyDetailsModel.objects.filter(
            is_active=True, is_deleted=False
        ).acount()
        print(f"[TenantDashboardConsumer] properties count: {props}")

        t_reqs = await TenantInterestRequestModel.objects.filter(
            tenant=t,
            is_active=True, is_deleted=False
        ).exclude(status='accepted').acount()

        # 2) Landlord-initiated requests
        l_reqs = await LandlordInterestRequestModel.objects.filter(
            tenant=t,
            is_active=True, is_deleted=False
        ).exclude(status='accepted').acount()

        total_reqs = t_reqs + l_reqs
        # 3) Pending appointments for this tenant
        appts = await AppointmentBookingModel.objects.filter(
            tenant=t, status="pending", is_active=True, is_deleted=False
        ).acount()
        print(f"[TenantDashboardConsumer] pending_appointments count: {appts}")

        # 4) Unread chat messages sent to this tenant
        chat_unread = await ChatMessageModel.objects.filter(
            receiver=f"tenant:{t.id}",
            is_read=False,
            is_active=True,
            is_deleted=False
        ).acount()
        print(f"[TenantDashboardConsumer] unread_chats count: {chat_unread}")

        # push the counts_update payload
        payload = {
            "action": "counts_update",
            "data": {
                "properties": props,
                "interest_requests": total_reqs,
                "pending_appointments": appts,
                "unread_chats": chat_unread,
            }
        }
        print(f"[TenantDashboardConsumer] sending counts payload: {payload}")
        await self.send_json(payload)

    async def disconnect(self, code):
        print(f"[TenantDashboardConsumer] disconnect(code={code}) called")
        if self.tenant:
            group_name = f"tenant_dashboard_{self.tenant.id}"
            await self.channel_layer.group_discard(
                group_name, self.channel_name
            )
            print(f"[TenantDashboardConsumer] removed from group: {group_name}")
