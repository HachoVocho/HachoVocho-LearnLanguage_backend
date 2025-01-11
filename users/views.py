
from hashlib import sha256
from rest_framework import generics, status
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Count, F

from listening_module.models import ListeningSentencesDataModel
from modules.models import TopicModel
from .models import UserLanguagePreferenceModel, UserListeningSentenceProgressModel, UserListeningTopicProgressModel, UserModel, OTPModel
from .serializers import OTPVerificationSerializer, UserLoginSerializer, UserSignupSerializer, UserTopicProgressSerializer
import random
from rest_framework.views import APIView
from response import Response as ResponseData
import os
import requests

def send_otp_via_google_script(email, otp):
    url = f"https://script.google.com/macros/s/{os.getenv('DATABASE_NAME', 'SEND_OTP_VIA_GOOGLE_SCRIPT_CODE')}/exec"
    data = {
        "email": email,
        "otp": otp,
    }
    response = requests.post(url, json=data)
    return response.json()

class UserSignupView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate OTP
        raw_otp = f"{user.email}{random.randint(1000, 9999)}"
        numeric_otp = str(abs(hash(raw_otp)) % 10**6)  # Ensure the OTP is 6 digits and numeric

        OTPModel.objects.create(user=user, code=numeric_otp)

        # Send OTP via Google Apps Script
        email_status = send_otp_via_google_script(user.email, numeric_otp)

        if email_status.get('success', False):  # Assuming success key in the response
            # Send a custom response if email sent successfully
            return Response(
                ResponseData.success_without_data(
                    "Otp sent on your email address"
                ),
                status=status.HTTP_201_CREATED,
            )
        else:
            # If email sending fails
            return Response(
                {"detail": "Failed to send OTP. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OTPVerificationView(APIView):
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response(
                {"detail": "Invalid email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            otp = OTPModel.objects.filter(user=user, code=code, is_used=False).latest('created_at')
        except OTPModel.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not otp.is_valid():
            return Response(
                {"detail": "OTP has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Validate language preference data
        comfortable_language_id = serializer.validated_data.get("comfortable_language_id")
        learning_language_id = serializer.validated_data.get("learning_language_id")
        UserLanguagePreferenceModel.objects.create(
            user=user,
            comfortable_language_id=comfortable_language_id,
            learning_language_id=learning_language_id
        )
        otp.is_used = True
        otp.save()
        user.is_active = True
        user.save()

        return Response(
            ResponseData.success_without_data("OTP verified successfully"),
            status=status.HTTP_200_OK
        )
    

class UserLoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response(
            ResponseData.error("Invalid Credentials"),
            status=status.HTTP_400_BAD_REQUEST
        )

        # Check the user’s password
        if not user.check_password(password):
            return Response(
            ResponseData.error("Invalid Credentials"),
            status=status.HTTP_400_BAD_REQUEST
        )

        # Ensure user is active (e.g., email verified)
        if not user.is_active:
            return Response(
            ResponseData.error("Please verify your email before logging in."),
            status=status.HTTP_400_BAD_REQUEST
        )

        # If everything is good, return success
        return Response(
            ResponseData.success(
                {
                    "user_id": user.id,
                }
            ,"User Logged In successfully"),
            status=status.HTTP_200_OK
        )
    

class FetchTopicsProgressView(APIView):
    """
    API to fetch topics progress for a user.
    """
    def post(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                ResponseData.error("User ID is required."),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Validate the user exists
            user = UserModel.objects.filter(id=user_id).first()
            user_language_preference = UserLanguagePreferenceModel.objects.filter(user_id=user_id).first()
            if not user or not user_language_preference:
                return Response(
                    ResponseData.error("Invalid User ID or missing language preferences."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch user language preferences
            comfortable_language = user_language_preference.comfortable_language
            learning_language = user_language_preference.learning_language

            # Query topics with levels
            grouped_topics_query = (
                TopicModel.objects.filter(is_active=True, is_deleted=False)
                .values('name', 'module__id', 'module__name', 'description', 'level__name', 'id')  # Include levels
                .order_by('module__name', 'name')
            )

            # Group topics manually
            topics_dict = {}
            for topic in grouped_topics_query:
                topic_key = (topic['name'], topic['module__id'])  # Group by topic name and module

                if topic_key not in topics_dict:
                    # Add a new topic entry
                    topics_dict[topic_key] = {
                        "topic_id": str(topic['id']),
                        "topic_name": topic['name'],
                        "module": {
                            "id": topic['module__id'],
                            "name": topic['module__name']
                        },
                        "description": topic['description'],
                        "levels_progress": []  # Initialize levels_progress list
                    }

                # Fetch progress for each level
                total_sentences = ListeningSentencesDataModel.objects.filter(
                    topic_id=topic['id'],
                    base_language=comfortable_language,
                    learning_language=learning_language
                ).count()

                completed_sentences = UserListeningSentenceProgressModel.objects.filter(
                    user_id=user_id,
                    sentence_data__topic_id=topic['id'],
                    is_listened=True,
                    sentence_data__base_language=comfortable_language,
                    sentence_data__learning_language=learning_language
                ).count()

                progress_percentage = (completed_sentences / total_sentences) * 100 if total_sentences > 0 else 0.0
                progress_entry = UserListeningTopicProgressModel.objects.filter(
                    user_id=user_id,
                    listening_sentence_data__topic_id=topic['id']
                ).first()
                did_listen_story = progress_entry.did_listen_story if progress_entry and total_sentences > 0 else False

                # Add level progress to the topic
                topics_dict[topic_key]["levels_progress"].append({
                    "level_name": topic['level__name'],
                    "progress_percentage": progress_percentage,
                    "completed_sentences": completed_sentences,
                    "total_sentences": total_sentences,
                    "did_listen_story": did_listen_story,
                })

            # Convert topics_dict values to a list
            progress_data = list(topics_dict.values())

            return Response(
                ResponseData.success(progress_data, "Topics progress fetched successfully."),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                ResponseData.error(f"Error fetching topics progress: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


        
class MarkSentenceListenedView(APIView):
    """
    API to mark a sentence as listened by the user.
    """
    def post(self, request):
        user_id = request.data.get('user_id')
        sentence_id = request.data.get('sentence_id')

        if not user_id or not sentence_id:
            return Response(
                ResponseData.error("User ID and Sentence ID are required."),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Validate the user exists
            user = UserModel.objects.filter(id=user_id).first()
            if not user:
                return Response(
                    ResponseData.error("Invalid User ID."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate the sentence exists
            sentence = ListeningSentencesDataModel.objects.filter(id=sentence_id).first()
            if not sentence:
                return Response(
                    ResponseData.error("Invalid Sentence ID."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update or create progress entry
            progress, created = UserListeningSentenceProgressModel.objects.get_or_create(
                user_id=user_id, sentence_data_id=sentence_id,
                defaults={"is_listened": False}
            )
            if not created:
                progress.is_listened = False
                progress.save()

            return Response(
                ResponseData.success_without_data("Sentence marked as listened."),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                ResponseData.error(f"Error updating sentence progress: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkStoryListenedView(APIView):
    """
    API to mark a story as listened for a topic by the user.
    """
    def post(self, request):
        user_id = request.data.get('user_id')
        topic_id = request.data.get('topic_id')

        if not user_id or not topic_id:
            return Response(
                ResponseData.error("User ID and Topic ID are required."),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            progress_records = UserListeningSentenceProgressModel.objects.filter(
                user_id=user_id, sentence__topic_id=topic_id
            )
            for record in progress_records:
                record.did_listen_story = True
                record.save()

            return Response(
                ResponseData.success_without_data("Story marked as listened."),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                ResponseData.error(f"Error updating story progress: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
