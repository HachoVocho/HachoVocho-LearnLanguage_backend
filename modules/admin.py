from django.contrib import admin
from .models import ModuleModel, TopicModel

@admin.register(ModuleModel)
class ModuleModelAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name']

@admin.register(TopicModel)
class TopicModelAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'module', 'created_at', 'updated_at']
    list_filter = ['name']
