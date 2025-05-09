# chat/consumers.py

import json
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q

from tenant.models import TenantDetailsModel

from .models import ChatMessageModel
from landlord.models import LandlordDetailsModel

# Keep track of who’s in each group
GROUP_MEMBERS = {}

#
# ─── Shared Base Logic ───────────────────────────────────────────────────────────
#
class _BaseChatConsumer(AsyncWebsocketConsumer):
    async def disconnect(self, close_code):
        if self.group_name:
            GROUP_MEMBERS.get(self.group_name, set()).discard(self.role)
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    def get_group_name(self, tenant_user, landlord_user):
        tid = tenant_user.split(":", 1)[1]
        lid = landlord_user.split(":", 1)[1]
        return f"chat_tenant_{tid}_landlord_{lid}"

    @database_sync_to_async
    def save_message(self, sender, receiver, message_text, read_status):
        msg = ChatMessageModel.objects.create(
            sender=sender, receiver=receiver,
            message=message_text, is_read=read_status
        )
        return msg.id

    @database_sync_to_async
    def get_messages_of_conversation(self, user, other):
        qs = ChatMessageModel.objects.filter(
            (Q(sender=user)&Q(receiver=other))|
            (Q(sender=other)&Q(receiver=user))
        ).order_by("created_at")
        return [
            {
                "id": m.id, "sender": m.sender,
                "receiver": m.receiver, "message": m.message,
                "is_read": m.is_read, "created_at": str(m.created_at)
            }
            for m in qs
        ]

    @database_sync_to_async
    def mark_messages_read(self, current_user, other_party):
        qs = ChatMessageModel.objects.filter(
            sender=other_party, receiver=current_user, is_read=False
        )
        print(f'svvdsvsdvdsvv {qs}')
        ids = list(qs.values_list("id", flat=True))
        qs.update(is_read=True)
        updated = ChatMessageModel.objects.filter(id__in=ids).order_by("created_at")
        print(f'updateddscds {updated}')
        return [
            {
                "id": m.id, "sender": m.sender,
                "receiver": m.receiver, "message": m.message,
                "is_read": m.is_read, "created_at": str(m.created_at)
            }
            for m in updated
        ]

#
# ─── Tenant Consumer ──────────────────────────────────────────────────────────────
#
class TenantChatConsumer(_BaseChatConsumer):
    async def connect(self):
        await self.accept()
        self.role = "tenant"
        self.group_name = None

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        print(f'data ${data}')
        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return
        if action == "connection_established":
            tenant_user = f"tenant:{data['sender'].split(':',1)[1]}"
            landlord_user = data["receiver"]
            group = self.get_group_name(tenant_user, landlord_user)
            self.group_name = group
            await self.channel_layer.group_add(group, self.channel_name)
            GROUP_MEMBERS.setdefault(group, set()).add("tenant")

            await self.send(text_data=json.dumps({
                "status":"success","action":"connection_established",
                "sender":tenant_user,"receiver":landlord_user,"role":"tenant"
            }))

        elif action == "send_message":
            sender = f"tenant:{data['sender'].split(':',1)[1]}"
            receiver = data["receiver"]
            text   = data["message"]
            group = self.get_group_name(sender, receiver)
            opposing = "landlord"
            read = opposing in GROUP_MEMBERS.get(group, ())
            new_message_id = await self.save_message(sender, receiver, text, read)

            payload = {
                "status":"success","action":"message_sent",
                "sender":sender,"receiver":receiver,
                "message_id" : new_message_id,
                "message":text,"timestamp":str(datetime.now()),
                "is_read":read
            }
            await self.channel_layer.group_send(
                group, {"type":"chat_message","message":payload}
            )

        elif action == "get_messages":
            sender = f"tenant:{data['sender'].split(':',1)[1]}"
            receiver = data.get("receiver")
            if receiver:
                group = self.get_group_name(sender, receiver)
                await self.channel_layer.group_add(group, self.channel_name)
                GROUP_MEMBERS.setdefault(group, set()).add("tenant")

                updated = await self.mark_messages_read(sender, receiver)
                await self.channel_layer.group_send(
                    group,
                    {"type":"chat_message","message":{
                        "status":"success","action":"messages_read_update",
                        "sender":sender,"messages":updated,
                        "timestamp":str(datetime.now())
                    }}
                )

            msgs = await self.get_messages_of_conversation(sender, receiver)
            await self.send(text_data=json.dumps({
                "status":"success","action":"messages_fetched",
                "sender": sender, "messages": msgs
            }))
            
        elif action == "search_summary":
            # New: filter the landlord's summary by query
            tenant_ref = f"tenant:{data['sender'].split(':',1)[1]}"
            full_summary = await self._get_tenant_chat_summary(tenant_ref)
            q = data.get("query", "").strip().lower()

            filtered = [
                item for item in full_summary
                if q in item["landlord_first_name"].lower()
                or q in item["landlord_last_name"].lower()
                or q in item["latest_message"].lower()
            ]

            await self.send(text_data=json.dumps({
                "status": "success",
                "action": "summary_fetched",
                "tenant": tenant_ref,
                "summary": filtered,
            }))


        elif action == "get_summary":
            print(f'incoming_data {data}')
            tenant_ref = data['sender']
            summary = await self._get_tenant_chat_summary(tenant_ref)
            await self.send(text_data=json.dumps({
                "status":"success","action":"summary_fetched",
                "tenant":tenant_ref,"summary":summary
            }))

        else:
            await self.send(text_data=json.dumps({
                "status":"error","message":"Invalid action"
            }))

    @database_sync_to_async
    def _get_tenant_chat_summary(self, tenant_ref):
        """
        Returns a list of dicts, one per landlord:
        {
        landlord_id,
        landlord_first_name,
        landlord_last_name,
        landlord_profile_picture,
        latest_message,
        latest_message_time,
        unread_count
        }
        """
        # Validate tenant reference format
        try:
            role, tenant_id = tenant_ref.split(":")
            if role != "tenant" or not tenant_id.isdigit():
                return []
        except (ValueError, AttributeError):
            return []

        # Get all conversations involving this tenant
        convos = ChatMessageModel.objects.filter(
            is_active=True,
            is_deleted=False
        ).filter(
            Q(sender=tenant_ref) | Q(receiver=tenant_ref)
        )

        # Extract unique landlord references
        landlord_refs = set()
        for msg in convos:
            if msg.sender.startswith("landlord:"):
                landlord_refs.add(msg.sender)
            elif msg.receiver.startswith("landlord:"):
                landlord_refs.add(msg.receiver)

        if not landlord_refs:
            return []

        # Pre-fetch all landlord details at once
        landlord_ids = []
        for ref in landlord_refs:
            try:
                _, lid = ref.split(":")
                landlord_ids.append(int(lid))
            except (ValueError, AttributeError):
                continue

        if not landlord_ids:
            return []

        landlords = LandlordDetailsModel.objects.filter(
            pk__in=landlord_ids
        ).in_bulk()

        summary = []
        for lref in landlord_refs:
            try:
                _, lpk = lref.split(":")
                print(f'lpk {lpk}')
                landlord_id = int(lpk)
                print(f'landlord_id {landlord_id}')
                landlord = landlords.get(landlord_id)
                print(f'landlord {landlord}')
                if not landlord:  # Skip if landlord not found
                    continue

                # Get conversation between this tenant and specific landlord
                convo = convos.filter(
                    (Q(sender=tenant_ref) & Q(receiver=lref)) |
                    (Q(sender=lref) & Q(receiver=tenant_ref))
                )
                print(f'convodff {convo}')
                latest = convo.order_by("-created_at").first()
                unread = convo.filter(
                    sender=lref, receiver=tenant_ref, is_read=False
                ).count()
                print(f'landlord {landlord.first_name}')
                summary.append({
                    "landlord_id": landlord_id,
                    "landlord_first_name": landlord.first_name or "",
                    "landlord_last_name": landlord.last_name or "",
                    "landlord_profile_picture": landlord.profile_picture.url if landlord.profile_picture else None,
                    "latest_message": latest.message if latest else "",
                    "latest_message_time": latest.created_at.isoformat() if latest else "",
                    "unread_count": unread,
                })
            except (ValueError, AttributeError):
                continue
        print(f'summarydff {summary}')
        # Sort by most recent message
        summary.sort(key=lambda x: x.get('latest_message_time', ''), reverse=True)

        return summary
#
# ─── Landlord Consumer ────────────────────────────────────────────────────────────
#
class LandlordChatConsumer(_BaseChatConsumer):
    async def connect(self):
        await self.accept()
        self.role = "landlord"
        self.group_name = None

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        print(f'incoming_data {data}')
        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return
        if action == "connection_established":
            landlord_user = f"landlord:{data['sender'].split(':',1)[1]}"
            tenant_user   = data["receiver"]
            group = self.get_group_name(tenant_user, landlord_user)
            self.group_name = group
            await self.channel_layer.group_add(group, self.channel_name)
            GROUP_MEMBERS.setdefault(group, set()).add("landlord")

            await self.send(text_data=json.dumps({
                "status":"success","action":"connection_established",
                "sender":landlord_user,"receiver":tenant_user,"role":"landlord"
            }))

        elif action == "send_message":
            sender   = f"landlord:{data['sender'].split(':',1)[1]}"
            receiver = data["receiver"]
            text     = data["message"]
            group    = self.get_group_name(receiver, sender)
            read     = "tenant" in GROUP_MEMBERS.get(group, ())
            new_message_id = await self.save_message(sender, receiver, text, read)

            payload = {
                "status":"success","action":"message_sent",
                "sender": sender, "receiver": receiver,
                'message_id':new_message_id,
                "message": text, "timestamp": str(datetime.now()),
                "is_read": read
            }
            await self.channel_layer.group_send(
                group, {"type":"chat_message","message":payload}
            )

        elif action == "get_messages":
            sender   = f"landlord:{data['sender'].split(':',1)[1]}"
            receiver = data.get("receiver")
            if receiver:
                group = self.get_group_name(receiver, sender)
                await self.channel_layer.group_add(group, self.channel_name)
                GROUP_MEMBERS.setdefault(group, set()).add("landlord")

                updated = await self.mark_messages_read(sender, receiver)
                await self.channel_layer.group_send(
                    group,
                    {"type":"chat_message","message":{
                        "status":"success","action":"messages_read_update",
                        "sender": sender, "messages": updated,
                        "timestamp": str(datetime.now())
                    }}
                )

            msgs = await self.get_messages_of_conversation(sender, receiver)
            await self.send(text_data=json.dumps({
                "status":"success","action":"messages_fetched",
                "sender": sender, "messages": msgs
            }))

        elif action == "get_summary":
            # New: landlord wants a summary of all tenant chats
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            summary = await self._get_landlord_chat_summary(landlord_ref)
            print(f'summary_landlord {summary}')
            await self.send(text_data=json.dumps({
                "status":"success",
                "action":"summary_fetched",
                "landlord": landlord_ref,
                "summary": summary,
            }))

        elif action == "search_summary":
            # New: filter the landlord's summary by query
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            full_summary = await self._get_landlord_chat_summary(landlord_ref)
            q = data.get("query", "").strip().lower()

            filtered = [
                item for item in full_summary
                if q in item["tenant_first_name"].lower()
                or q in item["tenant_last_name"].lower()
                or q in item["latest_message"].lower()
            ]

            await self.send(text_data=json.dumps({
                "status": "success",
                "action": "summary_fetched",
                "landlord": landlord_ref,
                "summary": filtered,
            }))

        else:
            await self.send(text_data=json.dumps({
                "status":"error","message":"Invalid action"
            }))

    @database_sync_to_async
    def _get_landlord_chat_summary(self, landlord_ref):
        """
        Returns a list of dicts, one per tenant:
        {
          tenant_id,
          tenant_first_name,
          tenant_last_name,
          tenant_profile_picture,
          latest_message,
          latest_message_time,
          unread_count
        }
        """
        convos = ChatMessageModel.objects.filter(
            is_active=True, is_deleted=False
        ).filter(
            Q(sender=landlord_ref) | Q(receiver=landlord_ref)
        )
        tenant_refs = set()
        for msg in convos:
            if msg.sender.startswith("tenant:"):
                tenant_refs.add(msg.sender)
            if msg.receiver.startswith("tenant:"):
                tenant_refs.add(msg.receiver)

        summary = []
        for tref in tenant_refs:
            _, tpk = tref.split(":")
            tenant_id = int(tpk)
            convo = convos.filter(
                (Q(sender=landlord_ref) & Q(receiver=tref)) |
                (Q(sender=tref) & Q(receiver=landlord_ref))
            )
            latest = convo.order_by("-created_at").first()
            unread = convo.filter(
                sender=tref, receiver=landlord_ref, is_read=False
            ).count()

            # You’ll need a TenantDetailsModel analogous to LandlordDetailsModel
            tenant = TenantDetailsModel.objects.filter(pk=tenant_id).first()
            pic_url = tenant.profile_picture.url if tenant and tenant.profile_picture else None

            summary.append({
                "tenant_id": tenant_id,
                "tenant_first_name": tenant.first_name if tenant else "",
                "tenant_last_name":  tenant.last_name  if tenant else "",
                "tenant_profile_picture": pic_url,
                "latest_message": latest.message if latest else "",
                "latest_message_time": latest.created_at.isoformat() if latest else "",
                "unread_count": unread,
            })

        return summary

