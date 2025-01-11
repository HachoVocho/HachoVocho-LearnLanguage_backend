from django.contrib import admin
from .models import UserLanguagePreferenceModel, UserListeningSentenceProgressModel, UserListeningTopicProgressModel, UserModel, OTPModel

# Customizing the User Admin Interface
@admin.register(UserModel)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_deleted', 'gender')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)  # Most recent users appear first
    readonly_fields = ('created_at', 'updated_at')

# Customizing the OTP Admin Interface
@admin.register(OTPModel)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created_at', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('user__email', 'code')
    readonly_fields = ('created_at',)


# Customizing the OTP Admin Interface
@admin.register(UserLanguagePreferenceModel)
class UserLanguagePreferenceModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comfortable_language','learning_language', 'created_at')
    search_fields = ('user__email', 'code')
    readonly_fields = ('created_at',)

# Customizing the OTP Admin Interface
@admin.register(UserListeningTopicProgressModel)
class UserListeningTopicProgressModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'progress_percentage','completed_sentences', 'did_listen_story')


# Customizing the OTP Admin Interface
@admin.register(UserListeningSentenceProgressModel)
class UserListeningSentenceProgressModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sentence_data','is_listened')

    