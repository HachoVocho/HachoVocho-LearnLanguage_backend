from django.contrib import admin
from .models import ChatMessageModel

@admin.register(ChatMessageModel)
class ChatMessageModelAdmin(admin.ModelAdmin):
    list_display = (
        'sender', 
        'receiver', 
        'message', 
        'is_read', 
        'is_active', 
        'is_deleted', 
        'created_at', 
        'updated_at'
    )
    list_filter = ('is_read', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('sender', 'receiver', 'message')
