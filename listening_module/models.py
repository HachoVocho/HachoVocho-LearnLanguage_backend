from django.db import models
from language_data.models import LanguageModel
from modules.models import TopicModel


class ListeningSentencesDataModel(models.Model):
    topic = models.ForeignKey(TopicModel, on_delete=models.CASCADE, related_name="listening_sentence_data_topic")
    base_language = models.ForeignKey(LanguageModel, on_delete=models.CASCADE, related_name="listening_data_base_language")
    learning_language = models.ForeignKey(LanguageModel, on_delete=models.CASCADE, related_name="listening_data_learning_language")
    sentence = models.CharField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.topic} - {self.sentence}"

class ListeningStoryDataModel(models.Model):
    listening_sentence_data = models.ForeignKey(ListeningSentencesDataModel, on_delete=models.CASCADE, related_name="listening_story_data_topic",null=True)
    story = models.CharField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.listening_sentence_data} - {self.story}"

