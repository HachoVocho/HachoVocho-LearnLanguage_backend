# help_support/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create_tenant_ticket/',        views.create_tenant_ticket),
    path('create_landlord_ticket/',      views.create_landlord_ticket),
    path('ticket_update_by_admin/',         views.admin_update_ticket),
    path('ticket_closed_by_user/',           views.user_close_ticket),
    path('list_tickets/',                 views.list_tickets),
]
