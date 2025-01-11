from django.contrib import admin
from .models import AllStaticStringsModel

@admin.register(AllStaticStringsModel)
class PageStaticStringAdmin(admin.ModelAdmin):
    list_display = ('id','language', 'is_active', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('language', 'is_active', 'is_deleted')