from django.contrib import admin
from .models import FaceToFaceConversationModel

@admin.register(FaceToFaceConversationModel)
class FaceToFaceConversationAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = (
        'user',
        'preferred_language',
        'learning_language',
        'learning_language_level',
        'created_at',
        'is_active',
    )
    # Fields to allow searching in the admin
    search_fields = (
        'user__username',  # Search by user's username
        'preferred_language__name',  # Search by preferred language name
        'learning_language__name',  # Search by learning language name
        'transcription',  # Search by transcription text
    )
    # Fields to filter by in the admin sidebar
    list_filter = (
        'preferred_language',
        'learning_language',
        'learning_language_level',
        'is_active',
        'created_at',
    )
    # Read-only fields for auditing
    readonly_fields = ('created_at', 'updated_at')

    # Fieldsets for detailed view in the admin
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Language Information', {
            'fields': ('preferred_language', 'learning_language', 'learning_language_level')
        }),
        ('Conversation Details', {
            'fields': ('transcription', 'translation', 'suggested_response_preferred', 'suggested_response_learning')
        }),
        ('Status', {
            'fields': ('is_active', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
