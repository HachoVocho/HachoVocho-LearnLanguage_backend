from rest_framework import serializers
from .models import ChatMessageModel

class ChatMessageCreateSerializer(serializers.Serializer):
    """
    Serializer to validate data for creating a chat message.
    Note: 'sender' will be set in the view from the logged-in user.
    """
    receiver = serializers.CharField(
        max_length=100,
        help_text='Receiver reference in the format "role:id", e.g., "tenant:12" or "landlord:5".'
    )
    message = serializers.CharField(
        max_length=1000,
        help_text="Text message to send."
    )

    def validate_receiver(self, value):
        """
        Ensure the receiver string is in the correct format: 'role:id'
        """
        try:
            role, pk = value.split(":")
            if role not in ["tenant", "landlord"]:
                raise serializers.ValidationError("Role must be either 'tenant' or 'landlord'.")
            int(pk)  # Ensure pk can be converted to an integer
        except (ValueError, TypeError):
            raise serializers.ValidationError("Receiver should be in the format 'role:id'.")
        return value

class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer to display chat message details.
    """
    class Meta:
        model = ChatMessageModel
        fields = [
            "id",
            "sender",
            "receiver",
            "message",
            "is_read",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
