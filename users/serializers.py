# users/serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import UserListeningTopicProgressModel, UserModel, OTPModel

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    gender = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    date_of_birth = serializers.DateField(required=False)

    class Meta:
        model = UserModel
        fields = ['first_name', 'last_name', 'email', 'password', 'gender', 'date_of_birth','app_language']

    def create(self, validated_data):
        user = UserModel.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            gender=validated_data.get('gender'),
            date_of_birth=validated_data.get('date_of_birth'),
            app_language=validated_data.get('app_language'),
        )
        return user

# users/serializers.py

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    comfortable_language_id = serializers.IntegerField()
    learning_language_id = serializers.IntegerField()

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserTopicProgressSerializer(serializers.ModelSerializer):
    topic_id = serializers.IntegerField(source='topic.id')
    topic_name = serializers.CharField(source='topic.name')

    class Meta:
        model = UserListeningTopicProgressModel
        fields = ['topic_id', 'topic_name', 'progress_percentage', 'completed_sentences', 'total_sentences', 'did_listen_story']