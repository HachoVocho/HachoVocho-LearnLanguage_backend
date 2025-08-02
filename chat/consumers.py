# chat/consumers.py
import json
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async
from googletrans import Translator,LANGUAGES
from notifications.send_notifications import send_onesignal_notification
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel
from user.refresh_count_for_groups import refresh_counts_for_groups
from user.ws_auth import authenticate_websocket
from .models import ChatMessageModel


translator = Translator()
# ────────────────────────────────────────────────────────────────────────────────
# util helpers
# ────────────────────────────────────────────────────────────────────────────────
def make_group_name(tenant_ref: str, landlord_ref: str) -> str:
    """
    Build the stable Channels/Redis group name out of user refs.

    >>> make_group_name("tenant:3", "landlord:8")
    'chat_tenant_3_landlord_8'
    """
    tid = tenant_ref.split(":", 1)[1]
    lid = landlord_ref.split(":", 1)[1]
    return f"chat_tenant_{tid}_landlord_{lid}"


# Keeps a live view of “who is currently connected to which chat room”.
# Shape:  {"chat_tenant_3_landlord_8": {"tenant", "landlord"}, ...}
GROUP_MEMBERS: dict[str, set[str]] = {}


def _someone_in_group(group: str, role: str) -> bool:
    """True if *role* is present in GROUP_MEMBERS[group]."""
    return role in GROUP_MEMBERS.get(group, set())


# ────────────────────────────────────────────────────────────────────────────────
# Base consumer
# ────────────────────────────────────────────────────────────────────────────────
class _BaseChatConsumer(AsyncWebsocketConsumer):
    """
    Shared logic; both roles inherit from this.

    Each socket can join multiple room-groups (one per conversation tab the user
    opens).  We keep that list in `self.groups` so `disconnect()` can clean up
    every room we joined.
    """

    # --------------------------------------------------------------------- life-cycle
    async def connect(self):
        await self.accept()               # subclasses will still do auth etc.
        self.groups: set[str] = set()     # room group names we joined
        self.role:   str | None = None    # "tenant" | "landlord"

    async def disconnect(self, close_code):
        for grp in self.groups:
            GROUP_MEMBERS.get(grp, set()).discard(self.role)
            await self.channel_layer.group_discard(grp, self.channel_name)

    # --------------------------------------------------------------------- helpers
    async def _join_group(self, group: str, role: str):
        """Adds this socket to Channels *and* to our python bookkeeping."""
        await self.channel_layer.group_add(group, self.channel_name)
        self.groups.add(group)
        GROUP_MEMBERS.setdefault(group, set()).add(role)

    async def chat_message(self, event):
        """Relay message coming from channel layer → browser."""
        await self.send(text_data=json.dumps(event["message"]))

    # --------------------------------------------------------------------- DB helpers
    @database_sync_to_async
    def save_message(self, sender, receiver, text, read):
        sender_id = int(sender.split(":")[1])
        receiver_id = int(receiver.split(":")[1])
        sender_role = sender.split(":")[0]
        receiver_role = receiver.split(":")[0]

        sender_obj = (
            TenantDetailsModel.objects.filter(id=sender_id).first()
            if sender_role == "tenant"
            else LandlordDetailsModel.objects.filter(id=sender_id).first()
        )

        receiver_obj = (
            TenantDetailsModel.objects.filter(id=receiver_id).first()
            if receiver_role == "tenant"
            else LandlordDetailsModel.objects.filter(id=receiver_id).first()
        )

        sender_pref_lang = getattr(sender_obj.preferred_language, "code", "en")
        receiver_pref_lang = getattr(receiver_obj.preferred_language, "code", "en")

        # 1. Detect the actual language the sender wrote in
        try:
            detected = translator.detect(text)
            message_lang = detected.lang
        except Exception as e:
            print(f"[WARN] Language detection failed: {e}")
            message_lang = sender_pref_lang  # fallback

        # 2. Translate for receiver only if needed
        if message_lang != receiver_pref_lang:
            try:
                translated = translator.translate(text, src=message_lang, dest=receiver_pref_lang)
                receiver_text = translated.text
            except Exception as e:
                print(f"[WARN] Translation to receiver language failed: {e}")
                receiver_text = text  # fallback
        else:
            receiver_text = text  # no translation needed

        msg = ChatMessageModel.objects.create(
            sender=sender,
            receiver=receiver,
            original_message=text,
            translated_message=receiver_text,
            is_read=read
        )
        return msg, message_lang


    @database_sync_to_async
    def get_messages_of_conversation(self, user, other):
        qs = ChatMessageModel.objects.filter(
            (Q(sender=user) & Q(receiver=other)) |
            (Q(sender=other) & Q(receiver=user))
        ).order_by("created_at")
        return [self._serialize_msg(m, user) for m in qs]

    @database_sync_to_async
    def mark_messages_read(self, me, other):
        qs = ChatMessageModel.objects.filter(
            sender=other, receiver=me, is_read=False
        )
        ids = list(qs.values_list("id", flat=True))
        qs.update(is_read=True)
        fresh = ChatMessageModel.objects.filter(id__in=ids).order_by("created_at")
        return [self._serialize_msg(m, me) for m in fresh]

    # --------------------------------------------------------------------- static
    @staticmethod
    def _serialize_msg(m: ChatMessageModel, current_user_ref: str) -> dict:
        is_sender = m.sender == current_user_ref

        # Optional: re-detect original language for history (can be expensive)
        try:
            detected = translator.detect(m.original_message)
            original_language = detected.lang
        except Exception:
            original_language = None

        display_message = m.original_message if is_sender else m.translated_message
        return {
            "id": m.id,
            "sender": m.sender,
            "receiver": m.receiver,
            "original_message": m.original_message,
            "translated_message": m.translated_message,
            "original_language": original_language,
            "display_message": display_message,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat(),
        }



# ────────────────────────────────────────────────────────────────────────────────
# Tenant consumer
# ────────────────────────────────────────────────────────────────────────────────
class TenantChatConsumer(_BaseChatConsumer):
    async def connect(self):
        await super().connect()
        self.role = "tenant"

        user, err = await authenticate_websocket(self.scope)
        if isinstance(user, AnonymousUser):
            return await self.close(code=4001)

    # ------------------------------------------------------------------ main receive
    async def receive(self, text_data):
        data = json.loads(text_data)
        act = data.get("action")

        # simple heartbeat
        if data.get("type") == "ping":
            return await self.send(text_data=json.dumps({"type": "pong"}))

        # -------- handshake
        if act == "connection_established":
            tenant_ref   = f"tenant:{data['sender'].split(':',1)[1]}"
            landlord_ref = data["receiver"]
            group        = make_group_name(tenant_ref, landlord_ref)
            await self._join_group(group, "tenant")

            await self.send(text_data=json.dumps({
                "status": "success",
                "action": "connection_established",
                "sender": tenant_ref, "receiver": landlord_ref, "role": "tenant",
            }))
            return

        # -------- send message
        if act == "send_message":
            tenant_ref = f"tenant:{data['sender'].split(':',1)[1]}"
            landlord_ref = data["receiver"]
            group = make_group_name(tenant_ref, landlord_ref)

            read = _someone_in_group(group, "landlord")
            msg, message_lang = await self.save_message(tenant_ref, landlord_ref,
                                             data["message"], read)

            # dashboard refresh
            await refresh_counts_for_groups(
                [f"landlord_dashboard_{landlord_ref.split(':',1)[1]}"]
            )

            payload = {
                "status": "success", "action": "message_sent",
                "sender": tenant_ref, "receiver": landlord_ref,
                "message_id": msg.id,
                "original_message": msg.original_message,
                "translated_message": msg.translated_message,
                "original_language": message_lang,
                "timestamp": datetime.utcnow().isoformat(),
                "is_read": read,
            }
            await self.channel_layer.group_send(
                group, {"type": "chat_message", "message": payload}
            )

            if not read:        # landlord offline → push
                await sync_to_async(send_onesignal_notification, thread_sensitive=True)(
                    landlord_ids=[landlord_ref.split(":",1)[1]],
                    headings={"en": "Chat Message"},
                    contents={"en": f"Tenant says: {data['message']}"},
                    data={"result": payload, "type": "landlord_chat_message"},
                )
            return

        # -------- fetch messages
        if act == "get_messages":
            tenant_ref = f"tenant:{data['sender'].split(':',1)[1]}"
            landlord_ref = data.get("receiver")
            group = make_group_name(tenant_ref, landlord_ref)

            await self._join_group(group, "tenant")

            updated = await self.mark_messages_read(tenant_ref, landlord_ref)
            await self.channel_layer.group_send(
                group, {"type": "chat_message", "message": {
                    "status": "success", "action": "messages_read_update",
                    "sender": tenant_ref, "messages": updated,
                    "timestamp": datetime.utcnow().isoformat(),
                }}
            )

            msgs = await self.get_messages_of_conversation(tenant_ref, landlord_ref)
            return await self.send(text_data=json.dumps({
                "status": "success", "action": "messages_fetched",
                "sender": tenant_ref, "messages": msgs,
            }))

        # -------- summary (and search)
        if act in ("get_summary", "search_summary"):
            tenant_ref = f"tenant:{data['sender'].split(':',1)[1]}"
            summary = await self._get_tenant_chat_summary(tenant_ref)
            if act == "search_summary":
                q = data.get("query", "").lower()
                summary = [
                    s for s in summary if
                    q in s["landlord_first_name"].lower() or
                    q in s["landlord_last_name"].lower()  or
                    q in s["latest_message"].lower()
                ]
            if act == "get_summary":
                await refresh_counts_for_groups(
                    [f"tenant_dashboard_{tenant_ref.split(':')[1]}"]
                )
            return await self.send(text_data=json.dumps({
                "status": "success", "action": "summary_fetched",
                "tenant": tenant_ref, "summary": summary,
            }))

        # -------- unknown
        await self.send(text_data=json.dumps({
            "status": "error", "message": "Invalid action"
        }))

    # ---------------------------------------------------------------- DB summary helper
    @database_sync_to_async
    def _get_tenant_chat_summary(self, tenant_ref):
        # (unchanged from your version – trimmed for brevity)
        # … same code as before …
        convos = ChatMessageModel.objects.filter(
            is_active=True, is_deleted=False
        ).filter(Q(sender=tenant_ref) | Q(receiver=tenant_ref))

        landlord_refs = {
            (msg.sender if msg.sender.startswith("landlord:") else msg.receiver)
            for msg in convos
            if msg.sender.startswith("landlord:") or msg.receiver.startswith("landlord:")
        }

        landlord_ids = [int(ref.split(":")[1]) for ref in landlord_refs]
        landlords = LandlordDetailsModel.objects.in_bulk(landlord_ids)

        summary = []
        for lref in landlord_refs:
            lid = int(lref.split(":")[1])
            landlord = landlords.get(lid)
            if not landlord:
                continue
            convo = convos.filter(
                (Q(sender=tenant_ref) & Q(receiver=lref)) |
                (Q(sender=lref) & Q(receiver=tenant_ref))
            )
            latest = convo.order_by("-created_at").first()
            unread = convo.filter(sender=lref, receiver=tenant_ref,
                                  is_read=False).count()
            summary.append({
                "landlord_id": lid,
                "landlord_first_name": landlord.first_name or "",
                "landlord_last_name": landlord.last_name or "",
                "landlord_profile_picture":
                    landlord.profile_picture.url if landlord.profile_picture else None,
                "latest_message": latest.original_message if latest else "",
                "latest_message_time": latest.created_at.isoformat() if latest else "",
                "unread_count": unread,
            })
        summary.sort(key=lambda x: x["latest_message_time"], reverse=True)
        return summary


# ────────────────────────────────────────────────────────────────────────────────
# Landlord consumer (mirrors Tenant)
# ────────────────────────────────────────────────────────────────────────────────
class LandlordChatConsumer(_BaseChatConsumer):
    async def connect(self):
        await super().connect()
        self.role = "landlord"

        user, err = await authenticate_websocket(self.scope)
        if isinstance(user, AnonymousUser):
            return await self.close(code=4001)

    async def receive(self, text_data):
        data = json.loads(text_data)
        act = data.get("action")

        if data.get("type") == "ping":
            return await self.send(text_data=json.dumps({"type": "pong"}))

        if act == "connection_established":
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            tenant_ref   = data["receiver"]
            group        = make_group_name(tenant_ref, landlord_ref)
            await self._join_group(group, "landlord")

            await self.send(text_data=json.dumps({
                "status": "success", "action": "connection_established",
                "sender": landlord_ref, "receiver": tenant_ref, "role": "landlord",
            }))
            return

        if act == "send_message":
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            tenant_ref   = data["receiver"]
            group = make_group_name(tenant_ref, landlord_ref)

            read   = _someone_in_group(group, "tenant")
            msg, message_lang = await self.save_message(landlord_ref, tenant_ref,
                                             data["message"], read)

            await refresh_counts_for_groups(
                [f"tenant_dashboard_{tenant_ref.split(':',1)[1]}"]
            )

            payload = {
                "status": "success", "action": "message_sent",
                "sender": landlord_ref, "receiver": tenant_ref,
                "message_id": msg.id,
                "timestamp": datetime.utcnow().isoformat(),
                "original_message": msg.original_message,
                "translated_message": msg.translated_message,
                "original_language": message_lang,
                "is_read": read,
            }
            await self.channel_layer.group_send(
                group, {"type": "chat_message", "message": payload}
            )

            if not read:
                print(f'tenant_ref.split(":",1)[1] {tenant_ref.split(":",1)[1]}')
                await sync_to_async(send_onesignal_notification, thread_sensitive=True)(
                    tenant_ids=[tenant_ref.split(":",1)[1]],
                    headings={"en": "Chat Message"},
                    contents={"en": f"Landlord says: {data['message']}"},
                    data={"result": payload, "type": "tenant_chat_message"},
                )
            return

        if act == "get_messages":
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            tenant_ref   = data.get("receiver")
            group = make_group_name(tenant_ref, landlord_ref)
            await self._join_group(group, "landlord")

            updated = await self.mark_messages_read(landlord_ref, tenant_ref)
            await self.channel_layer.group_send(
                group, {"type": "chat_message", "message": {
                    "status": "success", "action": "messages_read_update",
                    "sender": landlord_ref, "messages": updated,
                    "timestamp": datetime.utcnow().isoformat(),
                }}
            )

            msgs = await self.get_messages_of_conversation(landlord_ref, tenant_ref)
            return await self.send(text_data=json.dumps({
                "status": "success", "action": "messages_fetched",
                "sender": landlord_ref, "messages": msgs,
            }))

        if act in ("get_summary", "search_summary"):
            landlord_ref = f"landlord:{data['sender'].split(':',1)[1]}"
            summary = await self._get_landlord_chat_summary(landlord_ref)
            if act == "search_summary":
                q = data.get("query", "").lower()
                summary = [
                    s for s in summary if
                    q in s["tenant_first_name"].lower() or
                    q in s["tenant_last_name"].lower()  or
                    q in s["latest_message"].lower()
                ]
            if act == "get_summary":
                await refresh_counts_for_groups(
                    [f"landlord_dashboard_{landlord_ref.split(':')[1]}"]
                )
            return await self.send(text_data=json.dumps({
                "status": "success", "action": "summary_fetched",
                "landlord": landlord_ref, "summary": summary,
            }))

        await self.send(text_data=json.dumps({
            "status": "error", "message": "Invalid action"
        }))

    # ------------------------------------------------ landlord summary (same logic, mirrored)
    @database_sync_to_async
    def _get_landlord_chat_summary(self, landlord_ref):
        convos = ChatMessageModel.objects.filter(
            is_active=True, is_deleted=False
        ).filter(Q(sender=landlord_ref) | Q(receiver=landlord_ref))

        tenant_refs = {
            (msg.sender if msg.sender.startswith("tenant:") else msg.receiver)
            for msg in convos
            if msg.sender.startswith("tenant:") or msg.receiver.startswith("tenant:")
        }

        tenant_ids = [int(ref.split(":")[1]) for ref in tenant_refs]
        tenants = TenantDetailsModel.objects.in_bulk(tenant_ids)

        summary = []
        for tref in tenant_refs:
            tid = int(tref.split(":")[1])
            tenant = tenants.get(tid)
            if not tenant:
                continue
            convo = convos.filter(
                (Q(sender=landlord_ref) & Q(receiver=tref)) |
                (Q(sender=tref) & Q(receiver=landlord_ref))
            )
            latest = convo.order_by("-created_at").first()
            if latest:
                is_sender = latest.sender == landlord_ref
                display_message = latest.original_message if is_sender else latest.translated_message
                latest_time = latest.created_at.isoformat()
            else:
                display_message = ""
                latest_time = ""
            unread = convo.filter(sender=tref, receiver=landlord_ref,
                                  is_read=False).count()
            summary.append({
                "tenant_id": tid,
                "tenant_first_name": tenant.first_name or "",
                "tenant_last_name": tenant.last_name or "",
                "tenant_profile_picture":
                    tenant.profile_picture.url if tenant.profile_picture else None,
                    "latest_message": display_message,
                    "latest_message_time": latest_time,
                "unread_count": unread,
            })
        summary.sort(key=lambda x: x["latest_message_time"], reverse=True)
        return summary
