from django.contrib import admin
from .models import ListeningSentencesDataModel, ListeningStoryDataModel

@admin.register(ListeningSentencesDataModel)
class ListeningSentencesDataModelAdmin(admin.ModelAdmin):
    list_display = ['id','topic', 'base_language', 'learning_language','sentence']
    search_fields = ['topic']

@admin.register(ListeningStoryDataModel)
class ListeningStoryDataModelAdmin(admin.ModelAdmin):
    list_display = ['id','story', 'listening_sentence_data']
    search_fields = ['story']
