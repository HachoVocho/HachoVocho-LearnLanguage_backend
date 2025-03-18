from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('user.urls')),  # Include the user app's URLs
    path('tenant/', include('tenant.urls')),  # Include the tenant app's URLs
    path('landlord/', include('landlord.urls')),  # Include the landlord app's URLs
    path('localization/', include('localization.urls')),
    path('payments/', include('payments.urls')),
    path('landlord_availability/', include('landlord_availability.urls')),
    path('appointments/', include('appointments.urls')),
    path('translations/', include('translations.urls')),
    path('interest_requests/', include('interest_requests.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
