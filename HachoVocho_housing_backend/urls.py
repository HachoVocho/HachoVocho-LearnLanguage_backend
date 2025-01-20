from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('user.urls')),  # Include the user app's URLs
    path('tenant/', include('tenant.urls')),  # Include the tenant app's URLs
    path('landlord/', include('landlord.urls')) # Include the landlord app's URLs
]
