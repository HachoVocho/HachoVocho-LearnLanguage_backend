from collections import defaultdict
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FaceToFaceConversationModel
from .serializers import (
    FaceToFaceConversationSerializer, 
    FaceToFaceConversationInputSerializer
)
from response import Response as ResponseData

class GetFaceToFaceConversationsView(APIView):
    """
    API to fetch all face-to-face conversations for a given user, grouped by date.
    """

    def post(self, request):
        # Validate input using the serializer
        input_serializer = FaceToFaceConversationInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                ResponseData.error(input_serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = input_serializer.validated_data['user_id']

        try:
            # Fetch conversations for the given user
            conversations = FaceToFaceConversationModel.objects.filter(
                user_id=user_id, is_active=True, is_deleted=False
            ).order_by('-created_at')

            # If no conversations are found, return an appropriate message
            if not conversations.exists():
                return Response(
                    ResponseData.success([], "No conversations found for this user."),
                    status=status.HTTP_200_OK
                )

            # Serialize the data
            serializer = FaceToFaceConversationSerializer(conversations, many=True)

            # Group conversations by date
            grouped_data = defaultdict(list)
            for item in serializer.data:
                print(item.get('preferred_language'))
                created = item.get('created_at')
                if created:
                    # Convert the ISO date string to a datetime object
                    # Removing 'Z' if present to handle UTC format correctly
                    date_obj = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                    # Use desired date format (e.g., "9th July 2025")
                    date_key = date_obj.strftime("%d %B %Y, %A")
                    grouped_data[date_key].append(item)

            # Convert grouped_data to a list of dictionaries for structured response
            result = [{"date": date, "conversations": conv_list} for date, conv_list in grouped_data.items()]

            return Response(
                ResponseData.success(result, "Conversations fetched successfully."),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                ResponseData.error(f"Error fetching conversations: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
