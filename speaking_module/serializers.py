from rest_framework import serializers
from .models import FaceToFaceConversationModel

class FaceToFaceConversationSerializer(serializers.ModelSerializer):
    user_id = serializers.StringRelatedField()  # Display the user as a string
    preferred_language = serializers.StringRelatedField()
    learning_language = serializers.StringRelatedField()
    learning_language_level = serializers.StringRelatedField()

    class Meta:
        model = FaceToFaceConversationModel
        fields = [
            'id',
            'user_id',
            'preferred_language',
            'learning_language',
            'learning_language_level',
            'transcription',
            'translation',
            'suggested_response_preferred',
            'suggested_response_learning',
            'created_at',
        ]

from rest_framework import serializers

class FaceToFaceConversationInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True, error_messages={
        "required": "User ID is required.",
        "invalid": "User ID must be an integer."
    })
