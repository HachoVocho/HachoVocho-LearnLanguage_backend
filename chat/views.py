from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .serializers import ChatMessageCreateSerializer, ChatMessageSerializer
from .models import ChatMessageModel

# Import your tenant and landlord models
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel  # Replace 'your_app' with your actual app name
from response import Response as ResponseData


@api_view(["POST"])
def send_chat_message(request):
    """
    API to send a chat message.
    
    Expects:
        - receiver (string in format "tenant:<id>" or "landlord:<id>")
        - message (text)
        
    The sender is determined based on the logged-in user.
    """
    try:
        serializer = ChatMessageCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Determine sender reference based on request.user instance
            sender_obj = request.user
            if isinstance(sender_obj, TenantDetailsModel):
                sender_ref = f"tenant:{sender_obj.id}"
            elif isinstance(sender_obj, LandlordDetailsModel):
                sender_ref = f"landlord:{sender_obj.id}"
            else:
                return Response(
                    ResponseData.error("Invalid user type for sending message"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the chat message with sender set from logged-in user
            chat_message = ChatMessageModel.objects.create(
                sender=sender_ref,
                receiver=serializer.validated_data["receiver"],
                message=serializer.validated_data["message"]
            )
            
            # Serialize the newly created message for response
            serialized_message = ChatMessageSerializer(chat_message)
            return Response(
                ResponseData.success(serialized_message.data, "Message sent successfully"),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_chat_messages(request):
    """
    API to list all chat messages for the logged-in user.
    
    The endpoint returns messages where the logged-in user is either the sender or receiver.
    """
    try:
        sender_obj = request.user
        if isinstance(sender_obj, TenantDetailsModel):
            sender_ref = f"tenant:{sender_obj.id}"
        elif isinstance(sender_obj, LandlordDetailsModel):
            sender_ref = f"landlord:{sender_obj.id}"
        else:
            return Response(
                ResponseData.error("Invalid user type for fetching messages"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Retrieve messages where the user is either sender or receiver
        messages = ChatMessageModel.objects.filter(
            Q(sender=sender_ref) | Q(receiver=sender_ref),
            is_deleted=False,
            is_active=True
        ).order_by("created_at")
        
        serialized_messages = ChatMessageSerializer(messages, many=True)
        return Response(
            ResponseData.success(serialized_messages.data, "Messages fetched successfully"),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
