# chat/admin.py

from django.contrib import admin
from .models import ChatMessageModel, ChatMessageTranslationModel
from django.utils.html import format_html

class ChatMessageTranslationInline(admin.TabularInline):
    model = ChatMessageTranslationModel
    extra = 0
    readonly_fields = ("language_code", "translated_text", "created_at")
    fields = ("language_code", "translated_text", "created_at")

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
        'updated_at',
    )
    list_filter = ('is_read', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('sender', 'receiver', 'message')

    inlines = [ChatMessageTranslationInline]


@admin.register(ChatMessageTranslationModel)
class ChatMessageTranslationModelAdmin(admin.ModelAdmin):
    list_display = (
        'short_message',
        'language_code',
        'translated_text',
        'created_at',
    )
    list_filter = ('language_code', 'created_at')
    search_fields = ('message__message', 'translated_text')

    def short_message(self, obj):
        # show a truncated preview of the original message
        text = obj.message.message
        return text if len(text) < 50 else f"{text[:47]}…"
    short_message.short_description = 'Original Message'
