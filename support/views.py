# help_support/views.py
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from .models import TenantSupportTicket, LandlordSupportTicket
from .serializers import (
    TenantTicketCreateSerializer, LandlordTicketCreateSerializer,
    AdminTicketUpdateSerializer, UserTicketCloseSerializer,
    TicketListParamsSerializer
)
from django.db import models
from rest_framework.authentication import SessionAuthentication
from user.authentication import EnhancedJWTValidation
from response import Response as ResponseData

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def create_tenant_ticket(request):
    ser = TenantTicketCreateSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors), status=status.HTTP_400_BAD_REQUEST)
    t = TenantSupportTicket.objects.create(
        tenant_id   = ser.validated_data['tenant_id'],
        description = ser.validated_data['description']
    )
    return Response(ResponseData.success({"ticket_id": t.id}, "Ticket created"), status=status.HTTP_201_CREATED)

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def create_landlord_ticket(request):
    ser = LandlordTicketCreateSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors), status=status.HTTP_400_BAD_REQUEST)
    t = LandlordSupportTicket.objects.create(
        landlord_id = ser.validated_data['landlord_id'],
        description = ser.validated_data['description']
    )
    return Response(ResponseData.success({"ticket_id": t.id}, "Ticket created"), status=status.HTTP_201_CREATED)

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_update_ticket(request):
    ser = AdminTicketUpdateSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors), status=status.HTTP_400_BAD_REQUEST)
    data = ser.validated_data
    Model = TenantSupportTicket if data['ticket_type']=='tenant' else LandlordSupportTicket
    try:
        ticket = Model.objects.get(id=data['ticket_id'])
    except Model.DoesNotExist:
        return Response(ResponseData.error("Ticket not found"), status=status.HTTP_404_NOT_FOUND)
    ticket.admin_comment = data['admin_comment']
    ticket.status        = data['status']
    ticket.updated_by    = 'admin'
    ticket.save()
    return Response(ResponseData.success_without_data("Ticket updated"), status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def user_close_ticket(request):
    ser = UserTicketCloseSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ResponseData.error("Invalid data", ser.errors), status=status.HTTP_400_BAD_REQUEST)
    data = ser.validated_data
    Model = TenantSupportTicket if data['ticket_type']=='tenant' else LandlordSupportTicket
    try:
        ticket = Model.objects.get(id=data['ticket_id'])
    except Model.DoesNotExist:
        return Response(ResponseData.error("Ticket not found"), status=status.HTTP_404_NOT_FOUND)
    ticket.status     = 'closed'
    ticket.updated_by = data['ticket_type']
    ticket.save()
    return Response(ResponseData.success_without_data("Ticket closed"), status=status.HTTP_200_OK)
@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_tickets(request):
    """
    POST /api/help_support/list_tickets/
    Body: {
      "ticket_type": "tenant" | "landlord",
      "user_id": <integer>
    }
    """
    ser = TicketListParamsSerializer(data=request.data)
    if not ser.is_valid():
        return Response(
            ResponseData.error("Invalid data", ser.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    data = ser.validated_data
    Model = TenantSupportTicket if data['ticket_type'] == 'tenant' else LandlordSupportTicket
    # Build filter kwargs: {'tenant_id': X} or {'landlord_id': X}
    kwargs = {f"{data['ticket_type']}_id": data['user_id']}

    qs = Model.objects.filter(**kwargs).order_by(
        models.Case(
            models.When(status='open', then=0),
            models.When(status='inprogress', then=1),
            models.When(status='closed', then=2),
            default=3
        ),
        '-updated_at'
    )

    result = []
    for t in qs:
        result.append({
            "id":            t.id,
            "description":   t.description,
            "status":        t.status,
            "admin_comment": t.admin_comment,
            "updated_by":    t.updated_by,
            "created_at":    t.created_at.isoformat(),
            "updated_at":    t.updated_at.isoformat(),
        })

    return Response(
        ResponseData.success(result, "Tickets retrieved"),
        status=status.HTTP_200_OK
    )
