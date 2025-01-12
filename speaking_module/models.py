from django.db import models
from django.conf import settings
from language_data.models import LanguageModel, LanguageLevelModel
from users.models import UserModel


class FaceToFaceConversationModel(models.Model):
    # Relationship to the user who participated in the conversation
    user = models.ForeignKey(
        UserModel, 
        on_delete=models.CASCADE, 
        related_name='face_to_face_conversations'
    )
    
    # Preferred language (Foreign Key to LanguageModel)
    preferred_language = models.ForeignKey(
        LanguageModel, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='preferred_language_conversations'
    )
    
    # Learning language (Foreign Key to LanguageModel)
    learning_language = models.ForeignKey(
        LanguageModel, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='learning_language_conversations'
    )
    
    # Learning language level (Foreign Key to LanguageLevelModel)
    learning_language_level = models.ForeignKey(
        LanguageLevelModel, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='learning_level_conversations'
    )
    
    # Transcription of the conversation
    transcription = models.TextField(blank=True, null=True)
    
    # Translation of the conversation
    translation = models.TextField(blank=True, null=True)
    
    # Suggested response in preferred language
    suggested_response_preferred = models.TextField(blank=True, null=True)
    
    # Suggested response in learning language
    suggested_response_learning = models.TextField(blank=True, null=True)
    
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Conversation by {self.user} ({self.preferred_language.name} -> {self.learning_language.name})"
