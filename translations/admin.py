from django.contrib import admin
from .models import LanguageModel, TranslationModel

@admin.register(LanguageModel)
class LanguageModelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

@admin.register(TranslationModel)
class TranslationModelAdmin(admin.ModelAdmin):
    list_display = ('key', 'language', 'value')
    list_filter = ('language',)
    search_fields = ('key', 'value')
