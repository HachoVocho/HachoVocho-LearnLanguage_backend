from django.contrib import admin
from .models import LanguageModel, LanguageLevelModel

@admin.register(LanguageModel)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['id','name','translation_code', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name']

@admin.register(LanguageLevelModel)
class LanguageLevelAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['name']
