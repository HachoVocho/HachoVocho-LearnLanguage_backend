from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from .models import ChatMessageModel
from datetime import datetime
from django.db.models import Q

# Global dictionary to track roles present in each conversation group.
# Key: group_name, Value: set of roles (e.g. {'tenant', 'landlord'})
GROUP_MEMBERS = {}

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.group_name = None
        self.role = None  # Will be set on connection_established

    async def disconnect(self, close_code):
        if self.group_name:
            if self.group_name in GROUP_MEMBERS:
                GROUP_MEMBERS[self.group_name].discard(self.role)
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            print(f"Disconnected. Current GROUP_MEMBERS: {GROUP_MEMBERS}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            print(f"Received data: {data}")
            print(f"Action: {action}")
            
            if action == 'connection_established':
                # Payload example:
                # { "action": "connection_established", "sender": "tenant:1", "receiver": "landlord:2" }
                current_user = data['sender']
                other_party = data['receiver']
                # Determine role based solely on the prefix.
                if current_user.startswith("tenant"):
                    self.role = "tenant"
                elif current_user.startswith("landlord"):
                    self.role = "landlord"
                else:
                    self.role = "unknown"
                # Determine the tenant and landlord user strings.
                # (Assuming one of current_user or other_party starts with "tenant")
                tenant_user = current_user if current_user.startswith("tenant") else other_party
                landlord_user = current_user if current_user.startswith("landlord") else other_party
                # Compute group name using fixed roles.
                group_name = self.get_group_name(tenant_user, landlord_user)
                self.group_name = group_name
                await self.channel_layer.group_add(group_name, self.channel_name)
                # Update global membership.
                if group_name in GROUP_MEMBERS:
                    GROUP_MEMBERS[group_name].add(self.role)
                else:
                    GROUP_MEMBERS[group_name] = {self.role}
                print(f"Updated GROUP_MEMBERS: {GROUP_MEMBERS}")
                # Acknowledge connection.
                await self.send(text_data=json.dumps({
                    'status': 'success',
                    'action': 'connection_established',
                    'sender': current_user,
                    'receiver': other_party,
                    'role': self.role
                }))

            elif action == 'send_message':
                # Payload example:
                # { "action": "send_message", "sender": "tenant:1", "receiver": "landlord:2", "message": "Hello" }
                sender = data['sender']
                receiver = data['receiver']
                message_text = data['message']
                print(f"send_message data: {data}")
                # Compute group name using fixed roles.
                tenant_user = sender if sender.startswith("tenant") else receiver
                landlord_user = sender if sender.startswith("landlord") else receiver
                group_name = self.get_group_name(tenant_user, landlord_user)
                # Check group membership: if the opposing role is connected then mark as read.
                # For example, if sender is tenant then opposing_role is landlord.
                opposing_role = "landlord" if sender.startswith("tenant") else "tenant"
                read_status = False
                if group_name in GROUP_MEMBERS and opposing_role in GROUP_MEMBERS[group_name]:
                    read_status = True
                # Save the message with read status.
                await self.save_message(sender, receiver, message_text, read_status)
                print(f"read_status: {read_status}")
                # Prepare payload.
                message_data = {
                    'status': 'success',
                    'action': 'message_sent',
                    'sender': sender,
                    'receiver': receiver,
                    'message': message_text,
                    'timestamp': str(datetime.now()),
                    'is_read': read_status,
                }
                print(f"Broadcasting message_data: {message_data}")
                # Broadcast the message to everyone in the group.
                await self.channel_layer.group_send(
                    group_name,
                    {
                        'type': 'chat_message',
                        'message': message_data,
                    }
                )

            elif action == 'get_messages':
                # Payload example:
                # { "action": "get_messages", "sender": "tenant:1", "receiver": "landlord:2" }
                current_user = data['sender']
                other_party = data.get('receiver')
                if other_party:
                    tenant_user = current_user if current_user.startswith("tenant") else other_party
                    landlord_user = current_user if current_user.startswith("landlord") else other_party
                    group_name = self.get_group_name(tenant_user, landlord_user)
                    await self.channel_layer.group_add(group_name, self.channel_name)
                    self.group_name = group_name
                    if group_name in GROUP_MEMBERS:
                        GROUP_MEMBERS[group_name].add(self.role or "unknown")
                    else:
                        GROUP_MEMBERS[group_name] = {self.role or "unknown"}
                    # If the connection is acting as the receiver, mark messages as read.
                    updated_messages = await self.mark_messages_read(current_user, other_party)
                    read_update = {
                        'status': 'success',
                        'action': 'messages_read_update',
                        'sender': current_user,
                        'messages': updated_messages,
                        'timestamp': str(datetime.now())
                    }
                    await self.channel_layer.group_send(
                        group_name,
                        {
                            'type': 'chat_message',
                            'message': read_update,
                        }
                    )
                messages = await self.get_messages_of_conversation(current_user,other_party)
                print(f"Fetched messages: {messages}")
                await self.send(text_data=json.dumps({
                    'status': 'success',
                    'action': 'messages_fetched',
                    'sender': current_user,
                    'messages': messages,
                }))

            else:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'message': 'Invalid action specified'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'status': 'error',
                'message': 'Invalid JSON format'
            }))
        except KeyError as e:
            await self.send(text_data=json.dumps({
                'status': 'error',
                'message': f"Missing required field: {e}"
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'status': 'error',
                'message': str(e)
            }))

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    def get_group_name(self, tenant_user, landlord_user):
        # Extract numeric IDs (assuming format "tenant:1" and "landlord:2")
        tenant_id = tenant_user.split(":")[1]
        landlord_id = landlord_user.split(":")[1]
        return f"chat_tenant_{tenant_id}_landlord_{landlord_id}"

    @database_sync_to_async
    def save_message(self, sender, receiver, message_text, read_status):
        ChatMessageModel.objects.create(
            sender=sender,
            receiver=receiver,
            message=message_text,
            is_read=read_status
        )

    @database_sync_to_async
    def get_messages_of_conversation(self, user, otherParty):
        messages = ChatMessageModel.objects.filter(
            (Q(sender=user) & Q(receiver=otherParty)) | (Q(sender=otherParty) & Q(receiver=user))
        ).order_by('created_at')
        return [
            {
                'id': message.id,
                'sender': message.sender,
                'receiver': message.receiver,
                'message': message.message,
                'is_read': message.is_read,
                'created_at': str(message.created_at),
            }
            for message in messages
        ]

    @database_sync_to_async
    def mark_messages_read(self, current_user, other_party):
        qs = ChatMessageModel.objects.filter(
            sender=other_party,
            receiver=current_user,
            is_read=False
        )
        # Capture the IDs of messages to be updated.
        updated_ids = list(qs.values_list('id', flat=True))
        # Mark those messages as read.
        qs.update(is_read=True)
        # Requery only the messages that were updated.
        updated_messages = ChatMessageModel.objects.filter(id__in=updated_ids).order_by('created_at')
        return [
            {
                'id': message.id,
                'sender': message.sender,
                'receiver': message.receiver,
                'message': message.message,
                'is_read': message.is_read,
                'created_at': str(message.created_at),
            }
            for message in updated_messages
        ]

